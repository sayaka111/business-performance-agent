# Failed and review-required cases

## orders_buyers_driver_001

Status: REVIEW_REQUIRED

- Frozen gmv_diagnosis accepts ['gross_gmv'], but Case/Expected requests orders; no substitute workflow or retargeting was used.

## orders_frequency_driver_001

Status: REVIEW_REQUIRED

- Impossible active-buyer constraint: Orders=90, distinct Buyers=100; every buyer needs at least one valid order with one customer identity.

## aov_units_driver_001

Status: REVIEW_REQUIRED

- Frozen gmv_diagnosis accepts ['gross_gmv'], but Case/Expected requests aov; no substitute workflow or retargeting was used.

## aov_price_driver_001

Status: REVIEW_REQUIRED

- Frozen gmv_diagnosis accepts ['gross_gmv'], but Case/Expected requests aov; no substitute workflow or retargeting was used.

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

## category_orders_illegal_contribution_001

Status: REVIEW_REQUIRED

- Frozen gmv_diagnosis accepts ['gross_gmv'], but Case/Expected requests orders; no substitute workflow or retargeting was used.

## evidence_boundary_paid_search_001

Status: FAIL

- WorkflowPathGrader: Required orders × channel analytical path was not executed
- PrimaryDriverGrader: top_dimension_driver: expected 'paid_search', observed '<not observed>'
- EvidenceGrader: Required claim not communicated: Orders下降主要集中在Paid Search
- EvidenceGrader: Required claim not communicated: 现有数据不足以判断Paid Search下降的进一步外部原因

