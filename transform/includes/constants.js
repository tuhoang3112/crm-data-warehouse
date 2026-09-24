// Business constants shared across models.
// Keep business rules here (not hardcoded inside SQL) so they are defined once.

// Internal test deals created by the Sales/MKT team to test the CRM.
// They are flagged (not deleted) in fact_deal via `is_test_deal` and must be
// excluded from every metric (see docs/metric-definitions.md).
const TEST_DEAL_IDS = [
  112173, 99709, 82678, 67506, 67390, 67388, 67387, 67384, 67382, 67381,
  65961, 64365, 64363, 23150, 23147, 23146, 22877, 21512, 19274, 2173
];

module.exports = { TEST_DEAL_IDS };
