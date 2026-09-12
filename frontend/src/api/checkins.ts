import { apiJson } from "./apiFetch";
import type { CheckInCreate, CheckInPublic } from "./types";

export function submitCheckin(data: CheckInCreate): Promise<CheckInPublic> {
  return apiJson<CheckInPublic>("/checkins", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
