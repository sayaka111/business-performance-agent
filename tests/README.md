# Software tests

普通 `python -m unittest discover -s tests -v` 永远离线，live test 在 discovery 中 skip。

- Core：test_calculations、test_knowledge_skills、test_runtime、test_interfaces。
- Integration：test_cli_integration、test_sqlite_adapter、test_gemini_provider、test_report_fallback。
- Isolation：test_live_isolation 验证有 Key 但未 opt-in 时不会创建网络 Client。
- Live：test_gemini_live，需显式模块调用、BPA_RUN_LIVE_TESTS=1、GEMINI_API_KEY。

SQLite support 测试只验证构建、读写边界与接口，不加载 Golden Set Expected，不是 Agent Eval。普通 discovery 仅使用 tests 中的软件验证。

- Eval infrastructure：test_eval_framework 验证构造、评分、隔离和 Runner 容错，不要求 Golden Cases 通过。
