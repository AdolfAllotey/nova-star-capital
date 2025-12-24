import { usePolling } from "./usePolling";
import {
  getPnL,
  getTrades,
  getWorst,
  getWorstSummary,
  getSentiment,
  getWhales,
  getMarketRegime,
} from "../lib/api";

export const usePnL           = () => usePolling(getPnL,          { interval: 60_000 });
export const useTrades        = () => usePolling(getTrades,       { interval: 10_000 });
export const useWorst         = () => usePolling(getWorst,        { interval: 60_000 });
export const useWorstSummary  = () => usePolling(getWorstSummary, { interval: 60_000 });
export const useSentiment     = () => usePolling(getSentiment,    { interval: 20_000 });
export const useWhales        = () => usePolling(getWhales,       { interval: 15_000 });
export const useMarketRegime  = () => usePolling(getMarketRegime, { interval: 90_000 });
