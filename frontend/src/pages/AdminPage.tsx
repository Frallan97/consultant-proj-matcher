import { useEffect, useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AvailabilityBadge } from "@/components/ui/AvailabilityBadge";
import { SkillTags } from "@/components/ui/SkillTags";
import type { Consultant } from "@/types/consultant";
import { getAllConsultants, deleteConsultant, deleteConsultantsBatch, uploadResume, getResumeDownloadUrl } from "@/lib/api";
import { PAGINATION, UI_CONSTANTS } from "@/lib/constants";
import { Loader2, Trash2, MoreVertical, ChevronLeft, ChevronRight, Upload, CheckCircle2, XCircle, FileText } from "lucide-react";

export function AdminPage() {
  const [consultants, setConsultants] = useState<Consultant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const menuRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(PAGINATION.DEFAULT_PAGE_SIZE);
  
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
      // Clear success message after timeout
      setTimeout(() => setUploadSuccess(false), UI_CONSTANTS.UPLOAD_SUCCESS_TIMEOUT);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Failed to upload resume");
    } finally {
      setUploading(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleDownloadResume = (resumeId: string, consultantName: string) => {
    const url = getResumeDownloadUrl(resumeId);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${consultantName.replace(/\s+/g, "_")}_resume.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="w-full bg-background overflow-x-hidden">
      <div className="container mx-auto px-3 sm:px-4 py-4 sm:py-8 md:py-16 max-w-6xl">
        <div className="space-y-4 sm:space-y-6">
          {/* PDF Upload Card */}
          <Card className="shadow-md">
            <CardHeader className="px-3 sm:px-6 pt-3 sm:pt-6 pb-2 sm:pb-4">
              <CardTitle className="text-xl sm:text-2xl font-semibold flex items-center gap-2">
                <Upload className="h-5 w-5 sm:h-6 sm:w-6" />
                Upload Resume PDF
              </CardTitle>
              <p className="text-muted-foreground text-xs sm:text-sm mt-1">
                Upload a PDF resume to add it to the consultant database. Drag and drop or click to select.
              </p>
            </CardHeader>
            <CardContent className="px-3 sm:px-6 pb-3 sm:pb-6">
              <div className="space-y-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                  disabled={uploading}
                />
                <div
                  onClick={handleUploadClick}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.currentTarget.classList.add("border-primary");
                  }}
                  onDragLeave={(e) => {
                    e.currentTarget.classList.remove("border-primary");
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    e.currentTarget.classList.remove("border-primary");
                    const file = e.dataTransfer.files[0];
                    if (file && file.type === "application/pdf") {
                      if (fileInputRef.current) {
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        fileInputRef.current.files = dataTransfer.files;
                        handleFileSelect({ target: fileInputRef.current } as React.ChangeEvent<HTMLInputElement>);
                      }
                    }
                  }}
                  className="border border-dashed border-border/50 rounded-lg p-4 sm:p-8 text-center cursor-pointer hover:border-primary/50 hover:bg-muted/30 transition-colors"
                >
                  <Upload className="h-6 w-6 sm:h-8 sm:w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-xs sm:text-sm font-medium mb-1">Click to upload or drag and drop</p>
                  <p className="text-xs text-muted-foreground">PDF files only</p>
                </div>
                <div className="flex items-center gap-2 sm:gap-4 flex-wrap">
                  <Button
                    onClick={handleUploadClick}
                    disabled={uploading}
                    className="flex items-center gap-2 text-xs sm:text-sm px-3 sm:px-4"
                  >
                    {uploading ? (
                      <>
                        <Loader2 className="h-3 w-3 sm:h-4 sm:w-4 animate-spin" />
                        <span className="hidden sm:inline">Uploading...</span>
                        <span className="sm:hidden">Uploading</span>
                      </>
                    ) : (
                      <>
                        <Upload className="h-3 w-3 sm:h-4 sm:w-4" />
                        <span className="hidden sm:inline">Select PDF File</span>
                        <span className="sm:hidden">Select File</span>
                      </>
                    )}
                  </Button>
                  {uploadSuccess && (
                    <div className="flex items-center gap-2 text-green-600 animate-in fade-in slide-in-from-left-2">
                      <CheckCircle2 className="h-4 w-4" />
                      <span className="text-sm font-medium">Resume uploaded successfully!</span>
                    </div>
                  )}
                  {uploadError && (
                    <div className="flex items-center gap-2 text-destructive animate-in fade-in slide-in-from-left-2">
                      <XCircle className="h-4 w-4" />
                      <span className="text-sm font-medium">{uploadError}</span>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Consultants List Card */}
          <Card className="shadow-md">
            <CardHeader className="px-3 sm:px-6 pt-3 sm:pt-6 pb-2 sm:pb-4">
              <div className="flex items-center justify-between flex-wrap gap-2 sm:gap-4">
                <div>
                  <CardTitle className="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-semibold text-primary">
                    Database Overview
                  </CardTitle>
                  <p className="text-muted-foreground mt-1 sm:mt-2 text-xs sm:text-sm">
                    Manage consultants in the database
                  </p>
                </div>
                {someSelected && (
                  <Button
                    onClick={handleDeleteBatch}
                    disabled={deleting}
                    variant="destructive"
                    size="lg"
                    className="text-xs sm:text-sm px-3 sm:px-4"
                  >
                    {deleting ? (
                      <>
                        <Loader2 className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2 animate-spin" />
                        <span className="hidden sm:inline">Deleting...</span>
                        <span className="sm:hidden">Deleting</span>
                      </>
                    ) : (
                      <>
                        <Trash2 className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                        <span className="hidden sm:inline">Delete Selected ({selectedIds.size})</span>
                        <span className="sm:hidden">Delete ({selectedIds.size})</span>
                      </>
                    )}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="px-3 sm:px-6 pb-3 sm:pb-6">
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
              <div className="space-y-3 sm:space-y-4">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-0">
                  <p className="text-xs sm:text-sm text-muted-foreground">
                    Total: {consultants.length} consultant(s) | Showing {startIndex + 1}-{Math.min(endIndex, consultants.length)} of {consultants.length}
                  </p>
                  <div className="flex items-center gap-2">
                    <label htmlFor="page-size" className="text-xs sm:text-sm text-muted-foreground">
                      Per page:
                    </label>
                    <select
                      id="page-size"
                      value={pageSize}
                      onChange={(e) => {
                        setPageSize(Number(e.target.value));
                        setCurrentPage(1);
                      }}
                      className="rounded-md border border-input bg-background px-2 py-1 text-xs sm:text-sm"
                    >
                      {PAGINATION.PAGE_SIZE_OPTIONS.map((size) => (
                        <option key={size} value={size}>
                          {size}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="border border-border/50 rounded-lg overflow-hidden">
                  <div className="overflow-x-auto -mx-3 sm:mx-0">
                    <table className="w-full min-w-[600px]">
                      <thead className="bg-muted/50 border-b border-border/50">
                        <tr>
                          <th className="px-2 sm:px-3 py-2 sm:py-3 text-left">
                            <input
                              type="checkbox"
                              checked={allVisibleSelected}
                              onChange={(e) => handleSelectAll(e.target.checked)}
                              className="rounded border-input cursor-pointer"
                            />
                          </th>
                          <th className="px-2 sm:px-3 py-2 sm:py-3 text-left text-xs sm:text-sm font-medium">Name</th>
                          <th className="px-2 sm:px-3 py-2 sm:py-3 text-left text-xs sm:text-sm font-medium">Skills</th>
                          <th className="px-2 sm:px-3 py-2 sm:py-3 text-left text-xs sm:text-sm font-medium">Availability</th>
                          <th className="px-2 sm:px-3 py-2 sm:py-3 text-center text-xs sm:text-sm font-medium">Resume</th>
                          <th className="px-2 sm:px-3 py-2 sm:py-3 text-right text-xs sm:text-sm font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/50">
                        {paginatedConsultants.map((consultant, index) => {
                          const hasId = !!consultant.id;
                          const isSelected = hasId && selectedIds.has(consultant.id!);
                          return (
                            <tr
                              key={consultant.id || `consultant-${consultant.name}`}
                              className={`hover:bg-muted/50 transition-colors ${
                                index % 2 === 0 ? "bg-background" : "bg-muted/20"
                              } ${isSelected ? "bg-primary/10" : ""}`}
                            >
                              <td className="px-2 sm:px-3 py-1 sm:py-2">
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
                              <td className="px-2 sm:px-3 py-1 sm:py-2 text-xs sm:text-sm leading-tight">{consultant.name}</td>
                              <td className="px-2 sm:px-3 py-1 sm:py-2">
                                <SkillTags skills={consultant.skills} maxVisible={3} size="sm" />
                              </td>
                              <td className="px-2 sm:px-3 py-1 sm:py-2">
                                <AvailabilityBadge availability={consultant.availability} variant="text" className="text-xs sm:text-sm leading-tight" />
                              </td>
                              <td className="px-2 sm:px-3 py-1 sm:py-2 text-center">
                                {consultant.resumeId ? (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7 sm:h-8 sm:w-8"
                                    onClick={() => handleDownloadResume(consultant.resumeId!, consultant.name)}
                                    title="Download resume PDF"
                                    aria-label="Download resume PDF"
                                  >
                                    <FileText className="h-3 w-3 sm:h-4 sm:w-4 text-primary" />
                                  </Button>
                                ) : (
                                  <span className="text-xs text-muted-foreground">—</span>
                                )}
                              </td>
                              <td className="px-2 sm:px-3 py-1 sm:py-2 text-right">
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
                                    className="h-7 w-7 sm:h-8 sm:w-8 p-0"
                                    title={hasId ? "More options" : "No ID available"}
                                  >
                                    <MoreVertical className="h-3 w-3 sm:h-4 sm:w-4" />
                                  </Button>
                                  {hasId && openMenuId === consultant.id && (
                                    <div className="absolute right-0 mt-1 w-28 sm:w-32 bg-background border border-border/50 rounded-md shadow-lg z-10 animate-in fade-in slide-in-from-top-2">
                                      <button
                                        onClick={() => handleDeleteOne(consultant.id!)}
                                        disabled={deleting}
                                        className="w-full text-left px-2 sm:px-3 py-1.5 sm:py-2 text-xs sm:text-sm text-destructive hover:bg-destructive/10 rounded-md flex items-center gap-1 sm:gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                      >
                                        <Trash2 className="h-3 w-3 sm:h-4 sm:w-4" />
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
                  <div className="flex flex-col sm:flex-row items-center justify-between pt-3 sm:pt-4 flex-wrap gap-3 sm:gap-4">
                    <div className="text-xs sm:text-sm text-muted-foreground">
                      Page {currentPage} of {totalPages}
                    </div>
                    <div className="flex items-center gap-1 sm:gap-2">
                      <Button
                        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        variant="outline"
                        size="sm"
                        className="text-xs sm:text-sm px-2 sm:px-3"
                      >
                        <ChevronLeft className="h-3 w-3 sm:h-4 sm:w-4 mr-0.5 sm:mr-1" />
                        <span className="hidden sm:inline">Previous</span>
                        <span className="sm:hidden">Prev</span>
                      </Button>
                      <div className="flex items-center gap-0.5 sm:gap-1">
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
                              className="w-7 h-7 sm:w-8 sm:h-8 p-0 text-xs sm:text-sm"
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
                        className="text-xs sm:text-sm px-2 sm:px-3"
                      >
                        <span className="hidden sm:inline">Next</span>
                        <span className="sm:hidden">Next</span>
                        <ChevronRight className="h-3 w-3 sm:h-4 sm:w-4 ml-0.5 sm:ml-1" />
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

