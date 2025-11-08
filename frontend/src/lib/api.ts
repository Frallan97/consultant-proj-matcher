import { Consultant } from "@/types/consultant";

const API_BASE_URL = "http://localhost:8000";

export async function getAllConsultants(): Promise<Consultant[]> {
  const response = await fetch(`${API_BASE_URL}/api/consultants`);
  if (!response.ok) {
    throw new Error(`Failed to fetch consultants: ${response.statusText}`);
  }
  const data = await response.json();
  return data.consultants || [];
}

export async function deleteConsultant(id: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await fetch(`${API_BASE_URL}/api/consultants/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Failed to delete consultant: ${response.statusText}`);
  }
  return await response.json();
}

export async function deleteConsultantsBatch(ids: string[]): Promise<{ success: boolean; message?: string; deleted_count?: number; errors?: Array<{ id: string; error: string }>; error?: string }> {
  const response = await fetch(`${API_BASE_URL}/api/consultants`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ids }),
  });
  if (!response.ok) {
    throw new Error(`Failed to delete consultants: ${response.statusText}`);
  }
  return await response.json();
}

export async function uploadResume(file: File): Promise<{ id: string; name: string; skills: string[]; experience: string; education: string; email: string; phone: string; full_text: string }> {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await fetch(`${API_BASE_URL}/api/resumes/upload`, {
    method: "POST",
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Failed to upload resume: ${response.statusText}`);
  }
  
  return await response.json();
}

export function getResumeDownloadUrl(resumeId: string): string {
  return `${API_BASE_URL}/api/resumes/${resumeId}/pdf`;
}

