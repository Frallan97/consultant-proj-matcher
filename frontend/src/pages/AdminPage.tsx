import { useEffect, useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Consultant } from "@/types/consultant";
import { getAllConsultants, deleteConsultant, deleteConsultantsBatch, uploadResume } from "@/lib/api";
import { Loader2, Trash2, MoreVertical, ChevronLeft, ChevronRight, Upload, CheckCircle2, XCircle } from "lucide-react";

function getAvailabilityColor(availability: Consultant["availability"]) {
  switch (availability) {
    case "available":
      return "text-green-600 dark:text-green-400";
    case "busy":
      return "text-yellow-600 dark:text-yellow-400";
    case "unavailable":
      return "text-red-600 dark:text-red-400";
    default:
      return "text-muted-foreground";
  }
}

function getAvailabilityLabel(availability: Consultant["availability"]) {
  switch (availability) {
    case "available":
      return "Available";
    case "busy":
      return "Busy";
    case "unavailable":
      return "Unavailable";
    default:
      return "Unknown";
  }
}

export function AdminPage() {
  const [consultants, setConsultants] = useState<Consultant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const menuRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  
  // PDF upload state
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchConsultants = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAllConsultants();
      // Log to debug ID issues
      if (data.length > 0 && !data[0].id) {
        console.warn("Consultants fetched but no IDs found. First consultant:", data[0]);
      }
      setConsultants(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch consultants");
      console.error("Error fetching consultants:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConsultants();
  }, []);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (openMenuId) {
        const menuElement = menuRefs.current[openMenuId];
        if (menuElement && !menuElement.contains(event.target as Node)) {
          setOpenMenuId(null);
        }
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [openMenuId]);

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      // Select all visible consultants with IDs
      const visibleIds = new Set(
        paginatedConsultants
          .map((c) => c.id)
          .filter((id): id is string => !!id)
      );
      // Merge with existing selections
      const newSelected = new Set(selectedIds);
      visibleIds.forEach((id) => newSelected.add(id));
      setSelectedIds(newSelected);
    } else {
      // Deselect only visible consultants
      const visibleIds = new Set(
        paginatedConsultants
          .map((c) => c.id)
          .filter((id): id is string => !!id)
      );
      const newSelected = new Set(selectedIds);
      visibleIds.forEach((id) => newSelected.delete(id));
      setSelectedIds(newSelected);
    }
  };

  const handleSelectOne = (id: string, checked: boolean) => {
    const newSelected = new Set(selectedIds);
    if (checked) {
      newSelected.add(id);
    } else {
      newSelected.delete(id);
    }
    setSelectedIds(newSelected);
  };

  const handleDeleteOne = async (id: string) => {
    if (!id) return;
    
    setOpenMenuId(null); // Close menu
    
    if (!window.confirm("Are you sure you want to delete this consultant?")) {
      return;
    }

    setDeleting(true);
    try {
      await deleteConsultant(id);
      await fetchConsultants();
      setSelectedIds(new Set());
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete consultant");
      console.error("Error deleting consultant:", err);
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteBatch = async () => {
    if (selectedIds.size === 0) return;

    const count = selectedIds.size;
    if (!window.confirm(`Are you sure you want to delete ${count} consultant(s)?`)) {
      return;
    }

    setDeleting(true);
    try {
      const ids = Array.from(selectedIds);
      await deleteConsultantsBatch(ids);
      await fetchConsultants();
      setSelectedIds(new Set());
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete consultants");
      console.error("Error deleting consultants:", err);
    } finally {
      setDeleting(false);
    }
  };

  const consultantsWithIds = consultants.filter((c) => c.id);
  const someSelected = selectedIds.size > 0;

  // Pagination calculations
  const totalPages = Math.ceil(consultants.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedConsultants = consultants.slice(startIndex, endIndex);
  const paginatedConsultantsWithIds = paginatedConsultants.filter((c) => c.id);
  
  // Check if all visible consultants are selected
  const allVisibleSelected = paginatedConsultantsWithIds.length > 0 && 
    paginatedConsultantsWithIds.every((c) => c.id && selectedIds.has(c.id));

  // Reset to page 1 when consultants change
  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(1);
    }
  }, [consultants.length, currentPage, totalPages]);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (file.type !== "application/pdf") {
      setUploadError("Please select a PDF file");
      return;
    }

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(false);

    try {
      await uploadResume(file);
      setUploadSuccess(true);
      // Refresh consultant list
      await fetchConsultants();
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      // Clear success message after 3 seconds
      setTimeout(() => setUploadSuccess(false), 3000);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Failed to upload resume");
    } finally {
      setUploading(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8 md:py-16 max-w-6xl">
        <div className="space-y-6">
          {/* PDF Upload Card */}
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle className="text-2xl font-bold">Upload Resume PDF</CardTitle>
              <p className="text-muted-foreground text-sm mt-1">
                Upload a PDF resume to add it to the consultant database
              </p>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                  disabled={uploading}
                />
                <div className="flex items-center gap-4">
                  <Button
                    onClick={handleUploadClick}
                    disabled={uploading}
                    className="flex items-center gap-2"
                  >
                    {uploading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      <>
                        <Upload className="h-4 w-4" />
                        Select PDF File
                      </>
                    )}
                  </Button>
                  {uploadSuccess && (
                    <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                      <CheckCircle2 className="h-4 w-4" />
                      <span className="text-sm">Resume uploaded successfully!</span>
                    </div>
                  )}
                  {uploadError && (
                    <div className="flex items-center gap-2 text-destructive">
                      <XCircle className="h-4 w-4" />
                      <span className="text-sm">{uploadError}</span>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Consultants List Card */}
          <Card className="shadow-lg">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-3xl md:text-4xl font-bold">
                    Database Overview
                  </CardTitle>
                  <p className="text-muted-foreground mt-2">
                    Manage consultants in the database
                  </p>
                </div>
                {someSelected && (
                  <Button
                    onClick={handleDeleteBatch}
                    disabled={deleting}
                    variant="destructive"
                    size="lg"
                  >
                    {deleting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Deleting...
                      </>
                    ) : (
                      <>
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete Selected ({selectedIds.size})
                      </>
                    )}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="ml-3 text-muted-foreground">Loading consultants...</span>
              </div>
            ) : error ? (
              <div className="text-center py-12">
                <p className="text-destructive mb-4">Error: {error}</p>
                <Button onClick={fetchConsultants} variant="outline">
                  Retry
                </Button>
              </div>
            ) : consultants.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No consultants found in the database.</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Total: {consultants.length} consultant(s) | Showing {startIndex + 1}-{Math.min(endIndex, consultants.length)} of {consultants.length}
                  </p>
                  <div className="flex items-center gap-2">
                    <label htmlFor="page-size" className="text-sm text-muted-foreground">
                      Per page:
                    </label>
                    <select
                      id="page-size"
                      value={pageSize}
                      onChange={(e) => {
                        setPageSize(Number(e.target.value));
                        setCurrentPage(1);
                      }}
                      className="rounded-md border border-input bg-background px-2 py-1 text-sm"
                    >
                      <option value="10">10</option>
                      <option value="25">25</option>
                      <option value="50">50</option>
                      <option value="100">100</option>
                    </select>
                  </div>
                </div>
                <div className="border rounded-lg overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-3 py-0.5 text-left">
                            <input
                              type="checkbox"
                              checked={allVisibleSelected}
                              onChange={(e) => handleSelectAll(e.target.checked)}
                              className="rounded border-input"
                            />
                          </th>
                          <th className="px-3 py-1 text-left text-sm font-medium">Name</th>
                          <th className="px-3 py-1 text-left text-sm font-medium">Skills</th>
                          <th className="px-3 py-1 text-left text-sm font-medium">Availability</th>
                          <th className="px-3 py-1 text-right text-sm font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {paginatedConsultants.map((consultant) => {
                          const hasId = !!consultant.id;
                          const isSelected = hasId && selectedIds.has(consultant.id!);
                          return (
                            <tr
                              key={consultant.id || `consultant-${consultant.name}`}
                              className="hover:bg-muted/30 transition-colors"
                            >
                              <td className="px-3 py-0.5">
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  disabled={!hasId}
                                  onChange={(e) => {
                                    if (hasId) {
                                      handleSelectOne(consultant.id!, e.target.checked);
                                    }
                                  }}
                                  className="rounded border-input disabled:opacity-50 disabled:cursor-not-allowed"
                                />
                              </td>
                              <td className="px-3 py-0.5 font-medium text-sm leading-tight">{consultant.name}</td>
                              <td className="px-3 py-0.5">
                                <div className="flex flex-wrap gap-1">
                                  {consultant.skills.slice(0, 3).map((skill, index) => (
                                    <span
                                      key={index}
                                      className="inline-flex items-center rounded-md bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary"
                                    >
                                      {skill}
                                    </span>
                                  ))}
                                  {consultant.skills.length > 3 && (
                                    <span className="inline-flex items-center rounded-md bg-muted px-1.5 py-0.5 text-xs font-medium text-muted-foreground">
                                      +{consultant.skills.length - 3}
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="px-3 py-0.5">
                                <span className={`text-sm leading-tight ${getAvailabilityColor(consultant.availability)}`}>
                                  {getAvailabilityLabel(consultant.availability)}
                                </span>
                              </td>
                              <td className="px-3 py-0.5 text-right">
                                <div className="relative inline-block" ref={(el) => {
                                  if (consultant.id) {
                                    menuRefs.current[consultant.id] = el;
                                  }
                                }}>
                                  <Button
                                    onClick={() => {
                                      if (hasId) {
                                        setOpenMenuId(openMenuId === consultant.id ? null : consultant.id!);
                                      }
                                    }}
                                    disabled={!hasId || deleting}
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 w-8 p-0"
                                    title={hasId ? "More options" : "No ID available"}
                                  >
                                    <MoreVertical className="h-4 w-4" />
                                  </Button>
                                  {hasId && openMenuId === consultant.id && (
                                    <div className="absolute right-0 mt-1 w-32 bg-background border border-input rounded-md shadow-lg z-10">
                                      <button
                                        onClick={() => handleDeleteOne(consultant.id!)}
                                        disabled={deleting}
                                        className="w-full text-left px-3 py-2 text-sm text-destructive hover:bg-destructive/10 rounded-md flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                      >
                                        <Trash2 className="h-4 w-4" />
                                        Delete
                                      </button>
                                    </div>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
                {totalPages > 1 && (
                  <div className="flex items-center justify-between pt-4">
                    <div className="text-sm text-muted-foreground">
                      Page {currentPage} of {totalPages}
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        variant="outline"
                        size="sm"
                      >
                        <ChevronLeft className="h-4 w-4 mr-1" />
                        Previous
                      </Button>
                      <div className="flex items-center gap-1">
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          let pageNum: number;
                          if (totalPages <= 5) {
                            pageNum = i + 1;
                          } else if (currentPage <= 3) {
                            pageNum = i + 1;
                          } else if (currentPage >= totalPages - 2) {
                            pageNum = totalPages - 4 + i;
                          } else {
                            pageNum = currentPage - 2 + i;
                          }
                          return (
                            <Button
                              key={pageNum}
                              onClick={() => setCurrentPage(pageNum)}
                              variant={currentPage === pageNum ? "default" : "outline"}
                              size="sm"
                              className="w-8 h-8 p-0"
                            >
                              {pageNum}
                            </Button>
                          );
                        })}
                      </div>
                      <Button
                        onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        variant="outline"
                        size="sm"
                      >
                        Next
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
        </div>
      </div>
    </div>
  );
}

