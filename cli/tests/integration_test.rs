//! Integration tests for AI SDK CLI.
//!
//! These tests run against a real OpenMetadata instance and require:
//! - AI_SDK_HOST: Base URL of the OpenMetadata instance
//! - AI_SDK_TOKEN: JWT authentication token
//!
//! Optional:
//! - AI_SDK_TEST_AGENT: Name of an agent to test invocation
//! - AI_SDK_RUN_CHAT_TESTS: Set to "true" to run chat tests - invoke and streaming (uses AI tokens)
//!
//! Run with: cargo test --test integration_test

use std::env;
use std::process::Command;
use std::sync::OnceLock;
use uuid::Uuid;

/// Static storage for dynamically created test agent
static TEST_AGENT: OnceLock<Option<String>> = OnceLock::new();

/// Check if integration tests should run (requires non-empty AI_SDK_HOST and AI_SDK_TOKEN)
fn should_run() -> bool {
    !env::var("AI_SDK_HOST").unwrap_or_default().is_empty()
        && !env::var("AI_SDK_TOKEN").unwrap_or_default().is_empty()
}

/// Check if chat tests should run (invoke + streaming - they use AI tokens)
fn chat_tests_enabled() -> bool {
    env::var("AI_SDK_RUN_CHAT_TESTS")
        .map(|v| v.to_lowercase() == "true")
        .unwrap_or(false)
}

/// Get the CLI binary path
fn cli_binary() -> String {
    // Use cargo's target directory
    let target_dir = env::var("CARGO_TARGET_DIR").unwrap_or_else(|_| "target".to_string());
    format!("{target_dir}/debug/ai-sdk")
}

/// Generate a unique name for test entities
fn unique_name(prefix: &str) -> String {
    format!("{}-test-{}", prefix, &Uuid::new_v4().to_string()[..8])
}

/// Helper to run CLI command with credentials
fn run_cli(args: &[&str]) -> std::process::Output {
    Command::new(cli_binary())
        .args(args)
        .env("AI_SDK_HOST", env::var("AI_SDK_HOST").unwrap_or_default())
        .env("AI_SDK_TOKEN", env::var("AI_SDK_TOKEN").unwrap_or_default())
        .output()
        .expect("Failed to execute CLI")
}

/// Get a test agent name - either from AI_SDK_TEST_AGENT env var or create one dynamically
fn get_test_agent() -> Option<String> {
    // First check env var
    if let Ok(name) = env::var("AI_SDK_TEST_AGENT") {
        return Some(name);
    }

    // Use the cached value if already created
    TEST_AGENT
        .get_or_init(|| {
            // Get the first persona name
            let output = run_cli(&["personas", "list", "--json"]);
            if !output.status.success() {
                eprintln!("Failed to list personas for test agent creation");
                return None;
            }

            let stdout = String::from_utf8_lossy(&output.stdout);
            // Try to parse the first persona name from JSON output
            // Format should be like: [{"name":"persona-name",...}]
            let persona_name = if let Some(start) = stdout.find("\"name\":\"") {
                let start = start + 8;
                stdout[start..]
                    .find('"')
                    .map(|end| stdout[start..start + end].to_string())
            } else {
                None
            };

            let persona = match persona_name {
                Some(p) => p,
                None => {
                    eprintln!("No personas found for test agent creation");
                    return None;
                }
            };

            // Create a test agent with discoveryAndSearch ability
            let agent_name = unique_name("cli-invoke-test-agent");
            let output = run_cli(&[
                "agents",
                "create",
                "--name",
                &agent_name,
                "--persona",
                &persona,
                "--description",
                "Auto-created agent for CLI integration testing",
                "--abilities",
                "discoveryAndSearch",
                "--api-enabled",
                "true",
            ]);

            if output.status.success() {
                eprintln!("Created test agent: {agent_name}");
                Some(agent_name)
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                eprintln!("Failed to create test agent: {stderr}");
                None
            }
        })
        .clone()
}

// ==================== Basic CLI Tests ====================

#[test]
fn test_cli_version() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let output = run_cli(&["--version"]);
    assert!(output.status.success());

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("ai-sdk"));
    println!("CLI version: {}", stdout.trim());
}

#[test]
fn test_cli_help() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let output = run_cli(&["--help"]);
    assert!(output.status.success());

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("agents"));
    assert!(stdout.contains("invoke"));
    assert!(stdout.contains("configure"));
}

#[test]
fn test_invalid_token_rejected() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let output = Command::new(cli_binary())
        .args(["agents", "list"])
        .env("AI_SDK_HOST", env::var("AI_SDK_HOST").unwrap())
        .env("AI_SDK_TOKEN", "invalid-token-12345")
        .output()
        .expect("Failed to execute CLI");

    // Should fail with auth error
    assert!(
        !output.status.success(),
        "Expected auth failure with invalid token"
    );

    let stderr = String::from_utf8_lossy(&output.stderr);
    // Should contain some auth-related error
    assert!(
        stderr.to_lowercase().contains("auth")
            || stderr.to_lowercase().contains("401")
            || stderr.to_lowercase().contains("unauthorized")
            || stderr.to_lowercase().contains("token"),
        "Expected auth error message, got: {stderr}"
    );
}

// ==================== Agent Operations Tests ====================

#[test]
fn test_list_agents() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let output = run_cli(&["agents", "list"]);

    // Should succeed (may have 0 agents but shouldn't error)
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("agents list failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    println!("Agents list output:\n{stdout}");
}

#[test]
fn test_list_agents_json() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    // CLI doesn't have --json for agents list, so just verify list works
    let output = run_cli(&["agents", "list"]);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("agents list failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    println!("Agents list output length: {} bytes", stdout.len());
}

#[test]
fn test_agent_info() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let agent_name = match env::var("AI_SDK_TEST_AGENT") {
        Ok(name) => name,
        Err(_) => {
            println!("Skipping: AI_SDK_TEST_AGENT not set");
            return;
        }
    };

    let output = run_cli(&["agents", "info", &agent_name]);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("agents info failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains(&agent_name));
    println!("Agent info:\n{stdout}");
}

#[test]
fn test_invoke_agent() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    if !chat_tests_enabled() {
        println!("Skipping: Chat tests disabled (set AI_SDK_RUN_CHAT_TESTS=true to enable)");
        return;
    }

    let agent_name = match get_test_agent() {
        Some(name) => name,
        None => {
            println!("Skipping: No test agent available");
            return;
        }
    };

    let output = run_cli(&[
        "invoke",
        &agent_name,
        "Hello, this is an integration test. Please respond briefly.",
    ]);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("invoke failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(!stdout.is_empty());
    println!(
        "Invoke response:\n{}",
        &stdout[..std::cmp::min(500, stdout.len())]
    );
}

#[test]
fn test_stream_agent() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    if !chat_tests_enabled() {
        println!("Skipping: Chat tests disabled (set AI_SDK_RUN_CHAT_TESTS=true to enable)");
        return;
    }

    let agent_name = match get_test_agent() {
        Some(name) => name,
        None => {
            println!("Skipping: No test agent available");
            return;
        }
    };

    // Use invoke with --stream flag for streaming test
    // Use a prompt that triggers tool use with discoveryAndSearch ability
    let output = run_cli(&[
        "invoke",
        &agent_name,
        "do we have any customer data",
        "--stream",
    ]);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("stream invoke failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(!stdout.is_empty(), "Streamed response should not be empty");
    println!(
        "Streamed response:\n{}",
        &stdout[..std::cmp::min(500, stdout.len())]
    );
}

// ==================== Persona Operations Tests ====================

#[test]
fn test_list_personas() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let output = run_cli(&["personas", "list"]);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("personas list failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    println!("Personas list output:\n{stdout}");
}

#[test]
fn test_list_personas_json() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let output = run_cli(&["personas", "list", "--json"]);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("personas list --json failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let trimmed = stdout.trim();
    assert!(
        trimmed.starts_with('[') || trimmed.starts_with('{'),
        "Expected JSON output, got: {trimmed}"
    );
}

#[test]
fn test_get_persona() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    // First list personas to get one that exists
    let list_output = run_cli(&["personas", "list", "--json"]);
    if !list_output.status.success() {
        println!("Skipping: Could not list personas");
        return;
    }

    let stdout = String::from_utf8_lossy(&list_output.stdout);
    // Parse JSON to get first persona name
    if let Ok(personas) = serde_json::from_str::<Vec<serde_json::Value>>(&stdout) {
        if personas.is_empty() {
            println!("Skipping: No personas available");
            return;
        }

        if let Some(name) = personas[0].get("name").and_then(|n| n.as_str()) {
            let output = run_cli(&["personas", "get", name]);

            if !output.status.success() {
                let stderr = String::from_utf8_lossy(&output.stderr);
                panic!("personas get failed: {stderr}");
            }

            let stdout = String::from_utf8_lossy(&output.stdout);
            assert!(
                stdout.contains(name),
                "Expected persona name in output: {stdout}"
            );
            println!("Persona info:\n{stdout}");
        }
    }
}

#[test]
fn test_create_persona() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let persona_name = unique_name("persona");
    let output = run_cli(&[
        "personas",
        "create",
        "--name",
        &persona_name,
        "--description",
        "Integration test persona",
        "--prompt",
        "You are a helpful test assistant.",
        "--display-name",
        "Test Persona",
    ]);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("personas create failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(
        stdout.to_lowercase().contains("success") || stdout.contains(&persona_name),
        "Expected success or persona name in output: {stdout}"
    );
    println!("Created persona:\n{stdout}");
}

// ==================== Bot Operations Tests ====================

#[test]
fn test_list_bots() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let output = run_cli(&["bots", "list"]);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("bots list failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    println!("Bots list output:\n{stdout}");
}

#[test]
fn test_list_bots_json() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let output = run_cli(&["bots", "list", "--json"]);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("bots list --json failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let trimmed = stdout.trim();
    assert!(
        trimmed.starts_with('[') || trimmed.starts_with('{'),
        "Expected JSON output, got: {trimmed}"
    );
}

#[test]
fn test_get_bot() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    // First list bots to get one that exists
    let list_output = run_cli(&["bots", "list", "--json"]);
    if !list_output.status.success() {
        println!("Skipping: Could not list bots");
        return;
    }

    let stdout = String::from_utf8_lossy(&list_output.stdout);
    if let Ok(bots) = serde_json::from_str::<Vec<serde_json::Value>>(&stdout) {
        if bots.is_empty() {
            println!("Skipping: No bots available");
            return;
        }

        if let Some(name) = bots[0].get("name").and_then(|n| n.as_str()) {
            let output = run_cli(&["bots", "get", name]);

            if !output.status.success() {
                let stderr = String::from_utf8_lossy(&output.stderr);
                panic!("bots get failed: {stderr}");
            }

            let stdout = String::from_utf8_lossy(&output.stdout);
            assert!(
                stdout.contains(name),
                "Expected bot name in output: {stdout}"
            );
            println!("Bot info:\n{stdout}");
        }
    }
}

// ==================== Ability Operations Tests ====================

#[test]
fn test_list_abilities() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let output = run_cli(&["abilities", "list"]);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("abilities list failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    println!("Abilities list output:\n{stdout}");
}

#[test]
fn test_list_abilities_json() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    let output = run_cli(&["abilities", "list", "--json"]);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        panic!("abilities list --json failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let trimmed = stdout.trim();
    assert!(
        trimmed.starts_with('[') || trimmed.starts_with('{'),
        "Expected JSON output, got: {trimmed}"
    );
}

#[test]
fn test_get_ability() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    // First list abilities to get one that exists
    let list_output = run_cli(&["abilities", "list", "--json"]);
    if !list_output.status.success() {
        println!("Skipping: Could not list abilities");
        return;
    }

    let stdout = String::from_utf8_lossy(&list_output.stdout);
    if let Ok(abilities) = serde_json::from_str::<Vec<serde_json::Value>>(&stdout) {
        if abilities.is_empty() {
            println!("Skipping: No abilities available");
            return;
        }

        if let Some(name) = abilities[0].get("name").and_then(|n| n.as_str()) {
            let output = run_cli(&["abilities", "get", name]);

            if !output.status.success() {
                let stderr = String::from_utf8_lossy(&output.stderr);
                panic!("abilities get failed: {stderr}");
            }

            let stdout = String::from_utf8_lossy(&output.stdout);
            assert!(
                stdout.contains(name),
                "Expected ability name in output: {stdout}"
            );
            println!("Ability info:\n{stdout}");
        }
    }
}

// ==================== Agent Info with Persona Tests ====================

#[test]
fn test_agent_info_includes_persona() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    // Step 1: Create a persona with a specific prompt
    let persona_name = unique_name("info-persona");
    let persona_prompt =
        "You are a test persona for verifying agent info includes persona details.";
    let create_persona_output = run_cli(&[
        "personas",
        "create",
        "--name",
        &persona_name,
        "--description",
        "Test persona for agent info integration test",
        "--prompt",
        persona_prompt,
    ]);

    if !create_persona_output.status.success() {
        let stderr = String::from_utf8_lossy(&create_persona_output.stderr);
        panic!("Failed to create persona: {stderr}");
    }
    println!("Created persona: {persona_name}");

    // Step 2: Create an agent with that persona
    let agent_name = unique_name("info-agent");
    let create_agent_output = run_cli(&[
        "agents",
        "create",
        "--name",
        &agent_name,
        "--description",
        "Test agent for verifying agent info includes persona",
        "--persona",
        &persona_name,
        "--api-enabled",
        "true",
    ]);

    if !create_agent_output.status.success() {
        let stderr = String::from_utf8_lossy(&create_agent_output.stderr);
        panic!("Failed to create agent: {stderr}");
    }
    println!("Created agent: {agent_name}");

    // Step 3: Fetch agent info and verify persona details are included
    let info_output = run_cli(&["agents", "info", &agent_name]);

    if !info_output.status.success() {
        let stderr = String::from_utf8_lossy(&info_output.stderr);
        panic!("agents info failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&info_output.stdout);
    println!("Agent info output:\n{stdout}");

    // Verify agent name is present
    assert!(
        stdout.contains(&agent_name),
        "Expected agent name '{agent_name}' in output"
    );

    // Verify persona name is present
    assert!(
        stdout.contains(&persona_name),
        "Expected persona name '{persona_name}' in output. Got:\n{stdout}"
    );

    // Verify "Persona:" label is present
    assert!(
        stdout.contains("Persona:"),
        "Expected 'Persona:' label in output. Got:\n{stdout}"
    );

    // Verify persona prompt is present (at least part of it)
    assert!(
        stdout.contains("Persona Prompt:"),
        "Expected 'Persona Prompt:' label in output. Got:\n{stdout}"
    );

    // Verify the actual prompt content is included
    assert!(
        stdout.contains("test persona for verifying"),
        "Expected persona prompt content in output. Got:\n{stdout}"
    );
}

#[test]
fn test_agent_info_with_abilities() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    // Step 1: Create a persona
    let persona_name = unique_name("abilities-persona");
    let create_persona_output = run_cli(&[
        "personas",
        "create",
        "--name",
        &persona_name,
        "--description",
        "Test persona for agent with abilities",
        "--prompt",
        "You are a test assistant with search abilities.",
    ]);

    if !create_persona_output.status.success() {
        let stderr = String::from_utf8_lossy(&create_persona_output.stderr);
        panic!("Failed to create persona: {stderr}");
    }

    // Step 2: Create an agent with abilities
    let agent_name = unique_name("abilities-agent");
    let create_agent_output = run_cli(&[
        "agents",
        "create",
        "--name",
        &agent_name,
        "--description",
        "Test agent with abilities for info test",
        "--persona",
        &persona_name,
        "--abilities",
        "discoveryAndSearch,dataQualityAndTesting",
        "--api-enabled",
        "true",
    ]);

    if !create_agent_output.status.success() {
        let stderr = String::from_utf8_lossy(&create_agent_output.stderr);
        panic!("Failed to create agent: {stderr}");
    }

    // Step 3: Fetch agent info and verify abilities are included
    let info_output = run_cli(&["agents", "info", &agent_name]);

    if !info_output.status.success() {
        let stderr = String::from_utf8_lossy(&info_output.stderr);
        panic!("agents info failed: {stderr}");
    }

    let stdout = String::from_utf8_lossy(&info_output.stdout);
    println!("Agent info output:\n{stdout}");

    // Verify abilities section is present
    assert!(
        stdout.contains("Abilities:"),
        "Expected 'Abilities:' section in output. Got:\n{stdout}"
    );

    // Verify persona is also present
    assert!(
        stdout.contains("Persona:"),
        "Expected 'Persona:' in output. Got:\n{stdout}"
    );

    assert!(
        stdout.contains(&persona_name),
        "Expected persona name '{persona_name}' in output. Got:\n{stdout}"
    );
}

// ==================== Agent CRUD Operations Tests ====================

#[test]
fn test_create_agent() {
    if !should_run() {
        println!("Skipping: AI_SDK_HOST and AI_SDK_TOKEN not set");
        return;
    }

    // First get a persona to use
    let list_output = run_cli(&["personas", "list", "--json"]);
    if !list_output.status.success() {
        println!("Skipping: Could not list personas");
        return;
    }

    let stdout = String::from_utf8_lossy(&list_output.stdout);
    if let Ok(personas) = serde_json::from_str::<Vec<serde_json::Value>>(&stdout) {
        if personas.is_empty() {
            println!("Skipping: No personas available to create agent");
            return;
        }

        if let Some(persona_name) = personas[0].get("name").and_then(|n| n.as_str()) {
            let agent_name = unique_name("agent");
            let output = run_cli(&[
                "agents",
                "create",
                "--name",
                &agent_name,
                "--description",
                "Integration test agent",
                "--persona",
                persona_name,
                "--api-enabled",
                "true",
            ]);

            if !output.status.success() {
                let stderr = String::from_utf8_lossy(&output.stderr);
                panic!("agents create failed: {stderr}");
            }

            let stdout = String::from_utf8_lossy(&output.stdout);
            assert!(
                stdout.to_lowercase().contains("success") || stdout.contains(&agent_name),
                "Expected success or agent name in output: {stdout}"
            );
            println!("Created agent:\n{stdout}");
        }
    }
}
