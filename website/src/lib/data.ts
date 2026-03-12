import type {
  EventStudyData,
  MultiSeriesData,
  RegressionTableData,
  SummaryStatsData,
  BalanceTableData,
  SiteMetadata,
  LeaveOneOutData,
} from "@/types";

import metadataJson from "../../public/data/site_metadata.json";
import mainJson from "../../public/data/event_study_main.json";
import intensityJson from "../../public/data/event_study_intensity.json";
import signedIntensityJson from "../../public/data/event_study_updown_intensity.json";
import intensityQuartilesJson from "../../public/data/event_study_intensity_quartiles.json";
import mainUrbanJson from "../../public/data/event_study_main_urban.json";
import intensityUrbanJson from "../../public/data/event_study_intensity_urban.json";
import placeboJson from "../../public/data/event_study_placebo.json";
import leaveOneOutJson from "../../public/data/leave_one_out_state.json";
import regressionJson from "../../public/data/regression_tables.json";
import summaryJson from "../../public/data/summary_stats.json";
import balanceJson from "../../public/data/balance_table.json";

export const metadata = metadataJson as SiteMetadata;
export const eventStudyMain = mainJson as EventStudyData;
export const eventStudyIntensity = intensityJson as EventStudyData;
export const eventStudySignedIntensity = signedIntensityJson as EventStudyData;
export const eventStudyIntensityQuartiles = intensityQuartilesJson as MultiSeriesData;
export const eventStudyMainUrban = mainUrbanJson as EventStudyData;
export const eventStudyIntensityUrban = intensityUrbanJson as EventStudyData;
export const eventStudyPlacebo = placeboJson as EventStudyData;
export const leaveOneOutState = leaveOneOutJson as LeaveOneOutData;
export const regressionTables = regressionJson as Record<string, RegressionTableData>;
export const summaryStats = summaryJson as SummaryStatsData;
export const balanceTable = balanceJson as BalanceTableData;
