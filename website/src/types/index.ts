export interface EventStudyPoint {
  tau: number;
  coef: number;
  se: number;
  ci_lo: number;
  ci_hi: number;
}

export interface EventStudyData {
  title: string;
  y_label: string;
  reference_tau: number;
  points: EventStudyPoint[];
}

export interface UpDownPoint {
  tau: number;
  coef: number;
  ci_lo: number;
  ci_hi: number;
  group: string;
}

export interface UpDownData {
  title: string;
  y_label: string;
  reference_tau: number;
  upzoned: EventStudyPoint[];
  downzoned: EventStudyPoint[];
}

export interface Coefficient {
  value: number | null;
  stars: string;
}

export interface RegressionVariable {
  label: string;
  coefficients: Coefficient[];
  standard_errors: (number | null)[];
}

export interface RegressionStat {
  label: string;
  values: string[];
}

export interface RegressionTableData {
  title: string;
  notes: string[];
  columns: string[];
  variables: RegressionVariable[];
  stats: RegressionStat[];
}

export interface HistogramBin {
  x0: number;
  x1: number;
  count: number;
}

export interface SummaryStatVariable {
  variable: string;
  count: number;
  mean: number;
  sd: number;
  min: number;
  p25: number;
  p50: number;
  p75: number;
  max: number;
  histogram?: HistogramBin[];
}

export interface SummaryStatsPanel {
  label: string;
  variables: SummaryStatVariable[];
}

export interface SummaryStatsData {
  title: string;
  columns: string[];
  variables: SummaryStatVariable[];
  panels?: SummaryStatsPanel[];
  notes?: string[];
}

export interface BalanceVariable {
  variable: string;
  control: number;
  treated: number;
  difference: number;
  stars: string;
}

export interface BalanceTableData {
  title: string;
  columns: string[];
  notes: string[];
  variables: BalanceVariable[];
}

export interface SeriesConfig {
  label: string;
  color: string;
  points: Array<{ tau: number; coef: number; ci_lo: number; ci_hi: number }>;
}

export interface MultiSeriesData {
  title: string;
  y_label: string;
  reference_tau: number;
  series: SeriesConfig[];
}

export interface SiteMetadata {
  title: string;
  subtitle: string;
  author: string;
  course: string;
  analysis_window: { start: number; end: number };
  n_observations: number;
  headline_coefficient: number;
  headline_pct: number;
  headline_description: string;
  sample_description: string;
  n_observations_regression: string;
}

export interface LeaveOneOutPoint {
  excluded_state: number;
  coef: number;
  se: number;
  ci_lo: number;
  ci_hi: number;
  n_obs: number;
}

export interface LeaveOneOutData {
  title: string;
  full_sample_coef: number | null;
  points: LeaveOneOutPoint[];
}
