export interface Consultant {
  id?: string;
  name: string;
  skills: string[];
  availability: "available" | "busy" | "unavailable" | string;
  matchScore?: number;
  experience?: string;
  hasResume?: boolean;
  resumeId?: string;
}

