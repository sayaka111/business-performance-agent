# Failed and review-required cases

## channel_gmv_drilldown_001

Status: FAIL

- CalculationGrader: paid_search_effect: expected -2000, observed '<not observed>'
- CalculationGrader: organic_effect: expected 0, observed '<not observed>'
- CalculationGrader: direct_effect: expected 0, observed '<not observed>'
- CalculationGrader: No contribution observed for gross_gmv / channel; required closure cannot be assessed
- WorkflowPathGrader: Required gross_gmv × channel analytical path was not executed
- PrimaryDriverGrader: top_dimension_driver: expected 'paid_search', observed '<not observed>'

## category_gmv_contribution_001

Status: FAIL

- CalculationGrader: category_a_effect: expected -2000, observed '<not observed>'
- CalculationGrader: category_b_effect: expected 0, observed '<not observed>'
- CalculationGrader: No contribution observed for gross_gmv / category; required closure cannot be assessed
- WorkflowPathGrader: Required gross_gmv × category analytical path was not executed
- PrimaryDriverGrader: top_dimension_driver: expected 'category_a', observed '<not observed>'

## evidence_boundary_paid_search_001

Status: FAIL

- WorkflowPathGrader: Required orders × channel analytical path was not executed
- PrimaryDriverGrader: top_dimension_driver: expected 'paid_search', observed '<not observed>'
- EvidenceGrader: Required claim not communicated: Orders下降主要集中在Paid Search
- EvidenceGrader: Required claim not communicated: 现有数据不足以判断Paid Search下降的进一步外部原因

