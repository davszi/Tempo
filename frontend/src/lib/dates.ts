// Local calendar dates keep the chart and reviews consistent around midnight.
export function todayISO(date = new Date()) {
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"), String(date.getDate()).padStart(2, "0")].join("-");
}
export function dateOffset(days: number) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return todayISO(date);
}
