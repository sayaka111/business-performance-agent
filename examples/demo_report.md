# GMV Diagnosis — Mock / synthetic example

非真实经营数据。固定周期见 [输入](gmv_input.json)，完整证据见 [结构化结果](demo_result.json)。

GMV 诊断状态：completed
gross_gmv 从 10000.0 变为 7350.0，变化 -2650.0（-26.50%）。
在 gross_gmv 的本层分解中，orders 是最大同向内部贡献项：effect=-2475，占本层同向贡献 93.40%。
在 orders 的本层分解中，buyers 是最大同向内部贡献项：effect=-23.8421，占本层同向贡献 95.37%。
在 buyers，维度 customer_type 的本层分解中，new 是最大同向内部贡献项：effect=-7，占本层同向贡献 58.33%。
停止原因：target_coverage_reached
以上为内部贡献定位，不证明外部因果；最终业务决策由人工完成。
