//! Offline end-to-end checks of the eval CLI; all HTTP calls target mock servers.

use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;
use std::process::{Command, Output};
use std::time::Duration;
use uuid::Uuid;
use wiremock::matchers::{body_json, header, method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

struct Workspace(PathBuf);

impl Workspace {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!("collate-evals-{}", Uuid::new_v4()));
        fs::create_dir(&path).unwrap();
        Self(path)
    }

    fn write(&self, name: &str, content: &str) {
        fs::write(self.0.join(name), content).unwrap();
    }

    fn json(&self, name: &str, content: Value) {
        self.write(name, &content.to_string());
    }

    fn read(&self, name: &str) -> Value {
        serde_json::from_slice(&fs::read(self.0.join(name)).unwrap()).unwrap()
    }

    fn cli(&self, args: &[&str], env: &[(&str, &str)]) -> Output {
        let mut command = Command::new(env!("CARGO_BIN_EXE_ai-sdk"));
        command
            .current_dir(&self.0)
            .arg("evals")
            .args(args)
            .env_remove("AI_SDK_HOST")
            .env_remove("AI_SDK_TOKEN")
            .env_remove("EVAL_JUDGE_TOKEN");
        for (key, value) in env {
            command.env(key, value);
        }
        command.output().unwrap()
    }
}

impl Drop for Workspace {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.0).unwrap();
    }
}

fn assert_success(output: &Output) {
    assert!(
        output.status.success(),
        "stdout: {}\nstderr: {}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn csv_handles_quoted_commas_newlines_and_multiple_conditions() {
    let ws = Workspace::new();
    ws.write("cases.csv", "id,question,expected_answer,contains,must_reference\nowner,\"Who owns revenue,\nand where is it?\",\"Finance owns revenue,\nand maintains it.\",Finance|maintains,\n");
    ws.json(
        "answers.json",
        json!({"owner": {"response": "Finance owns revenue, and maintains it."}}),
    );
    assert_success(&ws.cli(&["validate", "-f", "cases.csv"], &[]));
    assert_success(&ws.cli(
        &[
            "report",
            "-f",
            "cases.csv",
            "--answers",
            "answers.json",
            "-o",
            "run.json",
        ],
        &[],
    ));
    let report = ws.read("run.json");
    assert_eq!(
        report["results"][0]["case"]["question"],
        "Who owns revenue,\nand where is it?"
    );
    assert_eq!(report["results"][0]["status"], "PASS");
    let overwrite = ws.cli(
        &[
            "report",
            "-f",
            "cases.csv",
            "--answers",
            "answers.json",
            "-o",
            "run.json",
        ],
        &[],
    );
    assert!(!overwrite.status.success());
    assert_eq!(ws.read("run.json"), report);
}

#[test]
fn invalid_suites_fail_before_any_run() {
    let ws = Workspace::new();
    for suite in [
        json!([]),
        json!([{"id": "a", "question": "Q"}]),
        json!([{"id": "a", "question": "Q", "contains": [""]}]),
        json!([{"id": "a", "question": "Q", "expected_answer": " "}]),
        json!([{"id": "a", "question": "Q", "expectedAnswer": "A"}]),
        json!([{"id": "a", "question": "Q", "contains": ["A"]}, {"id": "a", "question": "Q", "contains": ["B"]}]),
    ] {
        ws.json("cases.json", suite);
        assert!(!ws
            .cli(&["validate", "-f", "cases.json"], &[])
            .status
            .success());
    }
    ws.write("cases.csv", "id,question,contains,contains\na,Q,A,B\n");
    assert!(!ws
        .cli(&["validate", "-f", "cases.csv"], &[])
        .status
        .success());
}

#[test]
fn lineage_references_count_and_sql_can_be_required_without_an_exact_reference() {
    let ws = Workspace::new();
    ws.write("cases.csv", "id,question,must_reference,require_sql\nlineage,Q,banking-redshift.dev.marts_wealth.fct_trades,false\nno_sql,Q,,true\nanswer_sql,Q,,true\n");
    ws.json("answers.json", json!({
        "lineage": {"response":"See the attached lineage.","components":[{"type":"lineage","content":{"fullyQualifiedName":"banking-redshift.dev.marts_wealth.fct_trades"}}]},
        "no_sql": {"response":"The total is 732,834"},
        "answer_sql": {"response":"The total is 732,834","components":[{"type":"table","content":{"isAnswer":true,"sqlQueryConfig":{"queryText":"SELECT SUM(total_commission) FROM dev.marts_wealth.fct_trades"}}}]}
    }));
    assert_success(&ws.cli(&["validate", "-f", "cases.csv"], &[]));
    assert!(!ws
        .cli(
            &[
                "report",
                "-f",
                "cases.csv",
                "--answers",
                "answers.json",
                "-o",
                "run.json"
            ],
            &[]
        )
        .status
        .success());
    let results = ws.read("run.json");
    assert_eq!(results["results"][0]["status"], "PASS");
    assert_eq!(results["results"][1]["status"], "FAIL");
    assert_eq!(results["results"][2]["status"], "PASS");
    ws.write("invalid.csv", "id,question,require_sql\na,Q,yes\n");
    assert!(!ws
        .cli(&["validate", "-f", "invalid.csv"], &[])
        .status
        .success());
}

#[test]
fn exact_grading_uses_answer_sql_and_exact_catalog_references() {
    let ws = Workspace::new();
    ws.json("cases.json", json!([
        {"id":"ok", "question":"Q", "expected_sql":"SELECT SUM(amount) FROM orders", "must_reference":["warehouse.db.orders"], "must_not_reference":["warehouse.db.old_orders"]},
        {"id":"markdown_sql", "question":"Q", "expected_sql":"SELECT 1"},
        {"id":"probe_sql", "question":"Q", "expected_sql":"SELECT 1"},
        {"id":"failed_sql", "question":"Q", "contains":["answer"]},
        {"id":"prefix", "question":"Q", "must_reference":["warehouse.db.orders"]},
        {"id":"no_trace", "question":"Q", "required_tools":["runMetric"]},
        {"id":"empty", "question":"Q", "not_contains":["error"]},
        {"id":"spoofed_row", "question":"Q", "expected_sql":"SELECT 1"},
        {"id":"sql_literal", "question":"Q", "expected_sql":"SELECT 'a  b'"},
        {"id":"missing", "question":"Q", "expected_answer":"A"}
    ]));
    ws.json("answers.json", json!({
        "ok":{"response":"Revenue from [Orders](#table/warehouse.db.orders)", "components":[{"type":"table", "content":{"isAnswer":true, "sqlQueryConfig":{"queryText":"SELECT SUM(amount) FROM orders"}}}]},
        "markdown_sql":{"response":"```sql\nSELECT 1\n```"},
        "probe_sql":{"response":"Answer", "components":[{"type":"table", "content":{"isAnswer":false,"sqlQueryConfig":{"queryText":"SELECT 1"}}}]},
        "failed_sql":{"response":"Answer", "components":[{"type":"code","content":{"codeType":"sql","codeContent":"SELECT 1","isAnswer":true,"status":"failed"}}]},
        "prefix":{"response":"[Orders](#table/warehouse.db.orders_backup)"},
        "no_trace":{"response":"I used runMetric"},
        "empty":{"response":" "},
        "spoofed_row":{"response":"Answer", "components":[{"type":"table", "content":{"rows":[{"queryText":"SELECT 1"}]}}]},
        "sql_literal":{"response":"Answer", "components":[{"type":"table", "content":{"sqlQueryConfig":{"queryText":"SELECT 'a b'"}}}]}
    }));
    assert!(!ws
        .cli(
            &[
                "report",
                "-f",
                "cases.json",
                "--answers",
                "answers.json",
                "-o",
                "run.json"
            ],
            &[]
        )
        .status
        .success());
    let report = ws.read("run.json");
    let statuses: Vec<_> = report["results"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| r["status"].as_str().unwrap())
        .collect();
    assert_eq!(
        statuses,
        ["PASS", "PASS", "FAIL", "FAIL", "FAIL", "FAIL", "FAIL", "FAIL", "FAIL", "ERROR"]
    );
    assert_eq!(report["complete"], true);
}

#[test]
fn sql_only_answers_use_sql_fences_as_a_fallback_to_structured_evidence() {
    let ws = Workspace::new();
    let examples = [
        (
            "fenced",
            json!({"response":"Query, not executed:\n```sql\nSELECT 1\n```"}),
            "SELECT 1",
            "PASS",
        ),
        (
            "tilde_fence",
            json!({"response":"~~~SQL\nSELECT 1\n~~~"}),
            "SELECT 1",
            "PASS",
        ),
        (
            "multiple",
            json!({"response":"```sql\nSELECT 0\n```\n\n```sql\nSELECT 1\n```"}),
            "SELECT 1",
            "PASS",
        ),
        (
            "code_component",
            json!({"response":"Query, not executed.","components":[{"type":"code","content":{"isAnswer":true,"codeType":"sql","codeContent":"SELECT 1"}}]}),
            "SELECT 1",
            "PASS",
        ),
        (
            "inline",
            json!({"response":"Use `SELECT 1`."}),
            "SELECT 1",
            "FAIL",
        ),
        (
            "untyped_fence",
            json!({"response":"```\nSELECT 1\n```"}),
            "SELECT 1",
            "FAIL",
        ),
        (
            "python_fence",
            json!({"response":"```python\nSELECT 1\n```"}),
            "SELECT 1",
            "FAIL",
        ),
        (
            "blank_fence",
            json!({"response":"```sql\n   \n```"}),
            "SELECT 1",
            "FAIL",
        ),
        (
            "literal_whitespace",
            json!({"response":"```sql\nSELECT 'a b'\n```"}),
            "SELECT 'a  b'",
            "FAIL",
        ),
        (
            "structured_first",
            json!({"response":"```sql\nSELECT 1\n```","components":[{"type":"table","content":{"isAnswer":true,"sqlQueryConfig":{"queryText":"SELECT 2"}}}]}),
            "SELECT 1",
            "FAIL",
        ),
        (
            "failed_component",
            json!({"response":"```sql\nSELECT 1\n```","components":[{"type":"table","content":{"isAnswer":true,"status":"failed"}}]}),
            "SELECT 1",
            "FAIL",
        ),
    ];
    ws.json("cases.json", json!(examples.iter().map(|(id, _, sql, _)| json!({
        "id": id, "question": "Write SQL without executing it.", "expected_sql": sql, "require_sql": true
    })).collect::<Vec<_>>()));
    ws.json(
        "answers.json",
        Value::Object(
            examples
                .iter()
                .map(|(id, answer, _, _)| (id.to_string(), answer.clone()))
                .collect(),
        ),
    );
    let output = ws.cli(
        &[
            "report",
            "-f",
            "cases.json",
            "--answers",
            "answers.json",
            "-o",
            "run.json",
        ],
        &[],
    );
    assert!(!output.status.success());
    let report = ws.read("run.json");
    assert_eq!(report["complete"], true);
    for (result, (id, _, _, status)) in report["results"]
        .as_array()
        .unwrap()
        .iter()
        .zip(examples.iter())
    {
        assert_eq!(result["status"], *status, "case {id}: {result}");
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn default_chat_uses_fresh_conversations_and_does_not_receive_references() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/api/v1/assistants/chatConversations"))
        .and(header("Authorization", "Bearer collate-secret"))
        .respond_with(ResponseTemplate::new(201).set_body_json(json!({"id":"fresh-conversation"})))
        .expect(2)
        .mount(&server)
        .await;
    Mock::given(method("POST")).and(path("/api/v1/agents/invoke"))
        .and(header("Cache-Control", "no-store"))
        .and(body_json(json!({"message":"Who owns revenue?","conversationId":"fresh-conversation","agentType":"PLANNER","agentMode":"CHAT_MODE"})))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({"conversationId":"fresh-conversation","response":"Finance", "components":[]}))).expect(2).mount(&server).await;
    let ws = Workspace::new();
    ws.json(
        "cases.json",
        json!([
            {"id":"a","question":"Who owns revenue?","expected_answer":"Finance"},
            {"id":"b","question":"Who owns revenue?","expected_answer":"Finance"}
        ]),
    );
    assert_success(&ws.cli(
        &["run", "-f", "cases.json", "-o", "run.json"],
        &[
            ("AI_SDK_HOST", &server.uri()),
            ("AI_SDK_TOKEN", "collate-secret"),
        ],
    ));
    assert_eq!(ws.read("run.json")["results"].as_array().unwrap().len(), 2);
    assert!(!fs::read_to_string(ws.0.join("run.json"))
        .unwrap()
        .contains("collate-secret"));
}

#[tokio::test(flavor = "multi_thread")]
async fn http_errors_do_not_prevent_other_cases_from_running() {
    let server = MockServer::start().await;
    Mock::given(path("/api/v1/assistants/chatConversations"))
        .respond_with(ResponseTemplate::new(201).set_body_json(json!({"id":"c"})))
        .mount(&server)
        .await;
    Mock::given(path("/api/v1/agents/invoke")).and(body_json(json!({"message":"broken","conversationId":"c","agentType":"PLANNER","agentMode":"CHAT_MODE"})))
        .respond_with(ResponseTemplate::new(503).set_body_string("sensitive error body")).mount(&server).await;
    Mock::given(path("/api/v1/agents/invoke")).and(body_json(json!({"message":"working","conversationId":"c","agentType":"PLANNER","agentMode":"CHAT_MODE"})))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({"response":"A"}))).mount(&server).await;
    let ws = Workspace::new();
    ws.json("cases.json", json!([{"id":"broken","question":"broken","expected_answer":"A"},{"id":"working","question":"working","expected_answer":"A"}]));
    assert!(!ws
        .cli(
            &["run", "-f", "cases.json", "-o", "run.json"],
            &[("AI_SDK_HOST", &server.uri()), ("AI_SDK_TOKEN", "token")]
        )
        .status
        .success());
    let report = ws.read("run.json");
    assert_eq!(report["results"][0]["status"], "ERROR");
    assert_eq!(report["results"][1]["status"], "PASS");
    assert!(!report.to_string().contains("sensitive error body"));
}

#[tokio::test(flavor = "multi_thread")]
async fn semantic_grading_keeps_the_answer_when_the_judge_is_malformed() {
    let server = MockServer::start().await;
    Mock::given(path("/judge")).and(header("Authorization","Bearer judge-secret"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({"choices":[{"finish_reason":"stop","message":{"content":"{\"passed\":\"true\",\"reasoning\":\"Looks good\"}"}}]}))).mount(&server).await;
    let ws = Workspace::new();
    ws.json(
        "cases.json",
        json!([{"id":"sql","question":"Revenue?","expected_sql":"SELECT SUM(amount) FROM orders"}]),
    );
    ws.json("answers.json",json!({"sql":{"response":"Revenue is 42", "components":[{"type":"table","content":{"isAnswer":true,"sqlQueryConfig":{"queryText":"SELECT SUM(o.amount) FROM orders o"}}}]}}));
    let url = format!("{}/judge", server.uri());
    let args = [
        "report",
        "-f",
        "cases.json",
        "--answers",
        "answers.json",
        "-o",
        "error.json",
        "--judge",
        "llm",
        "--judge-model",
        "test-judge",
        "--judge-url",
        &url,
    ];
    assert!(!ws
        .cli(&args, &[("EVAL_JUDGE_TOKEN", "judge-secret")])
        .status
        .success());
    let report = ws.read("error.json");
    assert_eq!(report["results"][0]["status"], "ERROR");
    assert_eq!(report["results"][0]["output"]["response"], "Revenue is 42");
    assert!(!report.to_string().contains("judge-secret"));
    server.reset().await;
    Mock::given(path("/judge")).respond_with(ResponseTemplate::new(200).set_body_json(json!({"choices":[{"finish_reason":"stop","message":{"content":"{\"passed\":true,\"reasoning\":\"Equivalent aggregation; the alias does not change the result.\"}"}}]}))).mount(&server).await;
    let mut success_args = args;
    success_args[6] = "pass.json";
    assert_success(&ws.cli(&success_args, &[("EVAL_JUDGE_TOKEN", "judge-secret")]));
    assert_eq!(ws.read("pass.json")["results"][0]["status"], "PASS");
}

#[tokio::test(flavor = "multi_thread")]
async fn case_deadline_produces_an_error_report() {
    let server = MockServer::start().await;
    Mock::given(path("/api/v1/assistants/chatConversations"))
        .respond_with(
            ResponseTemplate::new(201)
                .set_body_json(json!({"id":"c"}))
                .set_delay(Duration::from_secs(3)),
        )
        .mount(&server)
        .await;
    let ws = Workspace::new();
    ws.json(
        "cases.json",
        json!([{"id":"a","question":"Q","expected_answer":"A"}]),
    );
    assert!(!ws
        .cli(
            &[
                "run",
                "-f",
                "cases.json",
                "-o",
                "run.json",
                "--timeout",
                "1"
            ],
            &[("AI_SDK_HOST", &server.uri()), ("AI_SDK_TOKEN", "token")]
        )
        .status
        .success());
    let report = ws.read("run.json");
    assert_eq!(report["complete"], true);
    assert_eq!(report["results"][0]["status"], "ERROR");
}

#[test]
fn compare_detects_regressions_changes_removals_and_incomplete_runs() {
    let ws = Workspace::new();
    ws.json("cases.json",json!([{"id":"a","question":"Q","expected_answer":"A"},{"id":"b","question":"Q2","expected_answer":"B"}]));
    ws.json(
        "answers.json",
        json!({"a":{"response":"A"},"b":{"response":"B"}}),
    );
    assert_success(&ws.cli(
        &[
            "report",
            "-f",
            "cases.json",
            "--answers",
            "answers.json",
            "-o",
            "baseline.json",
        ],
        &[],
    ));
    assert_success(&ws.cli(&["compare", "baseline.json", "baseline.json"], &[]));
    let baseline = ws.read("baseline.json");
    for variant in ["regression", "changed", "removed", "incomplete", "judge"] {
        let mut candidate = baseline.clone();
        match variant {
            "regression" => candidate["results"][0]["status"] = json!("FAIL"),
            "changed" => candidate["results"][0]["case"]["question"] = json!("different question"),
            "removed" => {
                candidate["results"].as_array_mut().unwrap().pop();
                candidate["planned"] = json!(1);
            }
            "incomplete" => candidate["complete"] = json!(false),
            "judge" => candidate["judge"] = json!("llm"),
            _ => unreachable!(),
        }
        ws.json("candidate.json", candidate);
        assert!(
            !ws.cli(&["compare", "baseline.json", "candidate.json"], &[])
                .status
                .success(),
            "missed {variant}"
        );
    }
}
