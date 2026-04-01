import { v4 as uuidv4 } from "uuid";

export type JobStatus = {
  status: "queued" | "rendering" | "done" | "failed";
  url?: string;
  error?: string;
  compositionId: string;
  createdAt: number;
};

const jobStore = new Map<string, JobStatus>();

export function createJob(compositionId: string): string {
  const renderId = uuidv4();
  jobStore.set(renderId, {
    status: "queued",
    compositionId,
    createdAt: Date.now(),
  });
  return renderId;
}

export function getJob(id: string): JobStatus | undefined {
  return jobStore.get(id);
}

export function updateJob(id: string, update: Partial<JobStatus>): void {
  const existing = jobStore.get(id);
  if (!existing) {
    throw new Error(`Job ${id} not found in store`);
  }
  jobStore.set(id, { ...existing, ...update });
}

export default jobStore;
