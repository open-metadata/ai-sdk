from __future__ import annotations

from diff_parser import ChangedAsset, parse_changed_assets


def test_parse_changed_assets_detects_sql_and_schema_files() -> None:
    diff = """diff --git a/models/staging/stg_orders.sql b/models/staging/stg_orders.sql
index 111..222 100644
--- a/models/staging/stg_orders.sql
+++ b/models/staging/stg_orders.sql
@@ -1,2 +1,2 @@
-select id, status from raw.orders
+select id, status as order_status from raw.orders
diff --git a/models/staging/_schema.yml b/models/staging/_schema.yml
index 333..444 100644
--- a/models/staging/_schema.yml
+++ b/models/staging/_schema.yml
@@ -1,3 +1,5 @@
 models:
   - name: stg_orders
+    tests:
+      - not_null
diff --git a/README.md b/README.md
index 555..666 100644
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-old
+new
"""

    assets = parse_changed_assets(diff)

    assert assets == [
        ChangedAsset(
            name="stg_orders",
            path="models/staging/stg_orders.sql",
            kind="model",
            change_type="modified",
            diff="diff --git a/models/staging/stg_orders.sql b/models/staging/stg_orders.sql\n"
            "index 111..222 100644\n"
            "--- a/models/staging/stg_orders.sql\n"
            "+++ b/models/staging/stg_orders.sql\n"
            "@@ -1,2 +1,2 @@\n"
            "-select id, status from raw.orders\n"
            "+select id, status as order_status from raw.orders",
        ),
        ChangedAsset(
            name="_schema",
            path="models/staging/_schema.yml",
            kind="schema",
            change_type="modified",
            diff="diff --git a/models/staging/_schema.yml b/models/staging/_schema.yml\n"
            "index 333..444 100644\n"
            "--- a/models/staging/_schema.yml\n"
            "+++ b/models/staging/_schema.yml\n"
            "@@ -1,3 +1,5 @@\n"
            " models:\n"
            "   - name: stg_orders\n"
            "+    tests:\n"
            "+      - not_null",
        ),
    ]


def test_parse_changed_assets_handles_deleted_models() -> None:
    diff = """diff --git a/models/marts/fct_orders.sql b/models/marts/fct_orders.sql
deleted file mode 100644
index 111..000
--- a/models/marts/fct_orders.sql
+++ /dev/null
@@ -1,2 +0,0 @@
-select * from int_orders
"""

    assets = parse_changed_assets(diff)

    assert len(assets) == 1
    assert assets[0].name == "fct_orders"
    assert assets[0].path == "models/marts/fct_orders.sql"
    assert assets[0].kind == "model"
    assert assets[0].change_type == "deleted"
