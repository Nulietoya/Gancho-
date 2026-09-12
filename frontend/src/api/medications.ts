import { apiJson } from "./apiFetch";
import type {
  MedicationCreate,
  MedicationEventCreate,
  MedicationEventPublic,
  MedicationPublic,
  ScheduleCreate,
  SchedulePublic,
} from "./types";

export function listMedications(): Promise<MedicationPublic[]> {
  return apiJson<MedicationPublic[]>("/medications");
}

export function createMedication(data: MedicationCreate): Promise<MedicationPublic> {
  return apiJson<MedicationPublic>("/medications", { method: "POST", body: JSON.stringify(data) });
}

export function discontinueMedication(medicationId: string): Promise<MedicationPublic> {
  return apiJson<MedicationPublic>(`/medications/${medicationId}/discontinue`, { method: "POST" });
}

export function listSchedules(medicationId: string): Promise<SchedulePublic[]> {
  return apiJson<SchedulePublic[]>(`/medications/${medicationId}/schedules`);
}

export function createSchedule(medicationId: string, data: ScheduleCreate): Promise<SchedulePublic> {
  return apiJson<SchedulePublic>(`/medications/${medicationId}/schedules`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function createMedicationEvent(
  medicationId: string,
  scheduleId: string,
  data: MedicationEventCreate,
): Promise<MedicationEventPublic> {
  return apiJson<MedicationEventPublic>(`/medications/${medicationId}/schedules/${scheduleId}/events`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
