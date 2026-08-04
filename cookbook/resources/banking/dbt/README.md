# banking dbt project

dbt project for the banking cookbook demo. One model set, two warehouse
targets — `redshift` and `bigquery`, selected with `--target` (or by the parent
Makefile's `WAREHOUSE` variable).

See the parent [`cookbook/resources/banking/README.md`](../README.md) for full
setup instructions (environment variables, seed loading, model build commands).

```bash
# from the parent directory
make dbt                     # --target redshift
WAREHOUSE=bigquery make dbt  # --target bigquery
```

Models are warehouse-neutral. Where the dialects genuinely differ, the project
dispatches on `target.type` via the macros in `macros/`: `days_between`,
`safe_divide`, `to_decimal`, and `type_long_string`. Everything else uses dbt's
built-in cross-database macros.
