import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AvailabilityBadge } from "@/components/ui/AvailabilityBadge";
import { SkillTags } from "@/components/ui/SkillTags";
import { MatchScoreBadge } from "@/components/ui/MatchScoreBadge";
import { ConsultantCardSkeleton } from "@/components/ui/LoadingSkeleton";
import type { Consultant } from "@/types/consultant";
import type { ConsultantResultsState } from "@/types/navigation";
import { getResumeDownloadUrl, buildApiUrl, matchConsultantsByRoles, type RoleQuery, type RoleMatchResult } from "@/lib/api";
import { ArrowLeft, Loader2, FileText, Users, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";

export function ConsultantResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as ConsultantResultsState | null;
  const projectDescription = state?.projectDescription || "";
  const roles = state?.roles;
  
  const [roleResults, setRoleResults] = useState<RoleMatchResult[]>([]);
  const [consultants, setConsultants] = useState<Consultant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRoleBased, setIsRoleBased] = useState(false);
  const [expandedRoles, setExpandedRoles] = useState<Set<number>>(new Set());
  const [expandedDescriptions, setExpandedDescriptions] = useState<Set<string>>(new Set());
  const [expandedSkills, setExpandedSkills] = useState<Set<string>>(new Set());

  const handleBack = () => {
    navigate("/");
  };

  // Redirect to home if no data (direct navigation or page reload)
  useEffect(() => {
    // Use a small delay to ensure the component has rendered
    const timer = setTimeout(() => {
      if (!projectDescription && !roles) {
        navigate("/", { replace: true });
      }
    }, 100);
    
    return () => clearTimeout(timer);
  }, [projectDescription, roles, navigate]);

  // Fetch consultants from API
  useEffect(() => {
    if (!projectDescription && !roles) {
      return;
    }

    const fetchConsultants = async () => {
      setLoading(true);
      setError(null);
      
      try {
        if (roles && roles.length > 0) {
          // Role-based matching
          setIsRoleBased(true);
          const data = await matchConsultantsByRoles(roles);
          console.log("Role match response:", data);
          console.log("Role results:", data.roles);
          if (data.roles) {
            data.roles.forEach((roleResult, idx) => {
              console.log(`Role ${idx} (${roleResult.role.title}):`, roleResult.consultants?.length || 0, "consultants");
            });
          }
          setRoleResults(data.roles || []);
        } else if (projectDescription) {
          // Legacy single query matching
          setIsRoleBased(false);
          const endpoint = "/consultants/match";
          const url = buildApiUrl(endpoint);
          const response = await fetch(url, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ projectDescription }),
          });

          if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            const errorMessage = error.detail || error.error || response.statusText;
            throw new Error(`POST ${endpoint} (${response.status}): ${errorMessage}`);
          }

          const data = await response.json();
          setConsultants(data.consultants || []);
        }
      } catch (err) {
        let errorMessage = "Failed to fetch consultants";
        if (err instanceof Error) {
          errorMessage = err.message;
        } else {
          errorMessage = String(err);
        }
        setError(errorMessage);
        console.error("Error fetching consultants:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchConsultants();
  }, [projectDescription, roles]);

  const handleDownloadResume = (resumeId: string, consultantName: string) => {
    const url = getResumeDownloadUrl(resumeId);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${consultantName.replace(/\s+/g, "_")}_resume.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const toggleRoleExpanded = (roleIndex: number) => {
    const newExpanded = new Set(expandedRoles);
    if (newExpanded.has(roleIndex)) {
      newExpanded.delete(roleIndex);
    } else {
      newExpanded.add(roleIndex);
    }
    setExpandedRoles(newExpanded);
  };

  const toggleDescriptionExpanded = (consultantId: string) => {
    const newExpanded = new Set(expandedDescriptions);
    if (newExpanded.has(consultantId)) {
      newExpanded.delete(consultantId);
    } else {
      newExpanded.add(consultantId);
    }
    setExpandedDescriptions(newExpanded);
  };

  const toggleSkillsExpanded = (consultantId: string) => {
    const newExpanded = new Set(expandedSkills);
    if (newExpanded.has(consultantId)) {
      newExpanded.delete(consultantId);
    } else {
      newExpanded.add(consultantId);
    }
    setExpandedSkills(newExpanded);
  };

  const truncateAtSentence = (text: string, maxLength: number = 150): string => {
    if (!text || text.length <= maxLength) {
      return text;
    }
    
    // Find the last sentence ending before maxLength
    const truncated = text.substring(0, maxLength);
    const sentenceEndings = /[.!?]\s+/g;
    let lastMatch: RegExpMatchArray | null = null;
    let match: RegExpMatchArray | null;
    
    // Find all sentence endings in the truncated text
    while ((match = sentenceEndings.exec(truncated)) !== null) {
      lastMatch = match;
    }
    
    // If we found a sentence ending, truncate there
    if (lastMatch && lastMatch.index !== undefined) {
      return text.substring(0, lastMatch.index + 1) + "...";
    }
    
    // Otherwise, truncate at the last space before maxLength
    const lastSpace = truncated.lastIndexOf(" ");
    if (lastSpace > maxLength * 0.7) { // Only use space if it's not too early
      return text.substring(0, lastSpace) + "...";
    }
    
    // Fallback: just truncate at maxLength
    return truncated + "...";
  };

  // Show loading state while checking for data or redirecting
  if (!projectDescription && !roles) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background to-muted/20 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Redirecting to home...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-background overflow-x-hidden">
      <div className="container mx-auto px-3 sm:px-4 py-4 sm:py-8 md:py-16 max-w-6xl">
        <div className="space-y-4 sm:space-y-6">
          {/* Header with back button */}
          <div className="flex items-center gap-2 sm:gap-4">
            <Button
              variant="outline"
              size="icon"
              onClick={handleBack}
              aria-label="Go back to project description"
              className="h-8 w-8 sm:h-10 sm:w-10"
            >
              <ArrowLeft className="h-3 w-3 sm:h-4 sm:w-4" />
            </Button>
            <div>
              <h1 className="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-bold text-primary">
                Matching Consultants
              </h1>
              <p className="text-muted-foreground mt-1 text-xs sm:text-sm">Find the perfect team for your project</p>
            </div>
          </div>

          {/* Project Description Display */}
          {projectDescription && !isRoleBased && (
            <Card>
              <CardHeader className="px-3 sm:px-6 pt-3 sm:pt-6 pb-2 sm:pb-4">
                <CardTitle className="text-lg sm:text-xl font-semibold">Your Project Description</CardTitle>
              </CardHeader>
              <CardContent className="px-3 sm:px-6 pb-3 sm:pb-6">
                <p className="text-muted-foreground whitespace-pre-wrap leading-relaxed text-sm sm:text-base">{projectDescription}</p>
              </CardContent>
            </Card>
          )}

          {/* Consultants List */}
          <div className="space-y-4">
            {loading ? (
              <div className="space-y-4">
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <span className="ml-3 text-muted-foreground">Loading consultants...</span>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {[1, 2, 3, 4, 5, 6].map((i) => (
                    <ConsultantCardSkeleton key={i} />
                  ))}
                </div>
              </div>
            ) : error ? (
              <Card className="border border-destructive/50">
                <CardContent className="pt-6">
                  <div className="space-y-4">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0">
                        <svg
                          className="h-5 w-5 text-destructive"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                          />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="text-destructive font-medium mb-2">Error matching consultants</p>
                        <p className="text-muted-foreground">{error}</p>
                        {error.includes("No consultants found") && (
                          <p className="text-sm text-muted-foreground mt-3">
                            Visit the Admin page to upload consultant resumes.
                          </p>
                        )}
                      </div>
                    </div>
                    <Button
                      onClick={() => window.location.reload()}
                      variant="outline"
                      className="mt-4"
                    >
                      Retry
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : isRoleBased ? (
              // Role-based results display
              (() => {
                // Filter out roles with no consultants, but log for debugging
                const rolesWithConsultants = roleResults.filter((roleResult) => {
                  const consultants = roleResult.consultants;
                  const hasConsultants = consultants && Array.isArray(consultants) && consultants.length > 0;
                  if (!hasConsultants) {
                    console.log(`Filtering out role "${roleResult.role.title}" - no consultants (length: ${consultants?.length || 'undefined'})`);
                  }
                  return hasConsultants;
                });
                
                // Show message if no roles have consultants
                if (rolesWithConsultants.length === 0 && roleResults.length > 0) {
                  return (
                    <Card>
                      <CardContent className="pt-6">
                        <div className="flex flex-col items-center justify-center py-12">
                          <Users className="h-12 w-12 text-muted-foreground mb-4" />
                          <p className="text-muted-foreground text-center text-lg font-semibold">
                            No consultants found for the specified roles.
                          </p>
                          <p className="text-muted-foreground text-center text-sm mt-2">
                            Try adjusting your requirements or check back later.
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  );
                }
                
                // Show message if no roles at all
                if (roleResults.length === 0) {
                  return (
                    <Card>
                      <CardContent className="pt-6">
                        <div className="flex flex-col items-center justify-center py-12">
                          <Users className="h-12 w-12 text-muted-foreground mb-4" />
                          <p className="text-muted-foreground text-center text-lg font-semibold">
                            No roles specified.
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  );
                }
                
                // Display roles with consultants
                return (
                  <div className="space-y-8">
                    {rolesWithConsultants.map((roleResult, roleIndex) => (
                    <div key={roleIndex} className="space-y-4">
                      <Card className="border-l-2 border-l-primary">
                        <CardHeader className="px-3 sm:px-6 pt-3 sm:pt-6 pb-2 sm:pb-4">
                          <CardTitle className="text-lg sm:text-xl md:text-2xl font-semibold">{roleResult.role.title}</CardTitle>
                          <div className="mt-2">
                            {roleResult.role.description.length > 150 ? (
                              <>
                                <CardDescription className={`text-sm sm:text-base leading-relaxed ${!expandedRoles.has(roleIndex) ? 'line-clamp-2' : ''}`}>
                                  {roleResult.role.description}
                                </CardDescription>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => toggleRoleExpanded(roleIndex)}
                                  className="mt-2 h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                                >
                                  {expandedRoles.has(roleIndex) ? (
                                    <>
                                      <ChevronUp className="h-3 w-3 mr-1" />
                                      Show less
                                    </>
                                  ) : (
                                    <>
                                      <ChevronDown className="h-3 w-3 mr-1" />
                                      Show more
                                    </>
                                  )}
                                </Button>
                              </>
                            ) : (
                              <CardDescription className="text-sm sm:text-base leading-relaxed">
                                {roleResult.role.description}
                              </CardDescription>
                            )}
                          </div>
                          {roleResult.role.requiredSkills.length > 0 && (
                            <div className="mt-3">
                              <p className="text-xs sm:text-sm font-medium mb-2 text-muted-foreground">Required Skills:</p>
                              <SkillTags skills={roleResult.role.requiredSkills} />
                            </div>
                          )}
                        </CardHeader>
                      </Card>
                      <>
                        <h3 className="text-base sm:text-lg font-semibold flex items-center gap-2 px-1">
                          <Users className="h-4 w-4 sm:h-5 sm:w-5" />
                          {roleResult.consultants.length} {roleResult.consultants.length === 1 ? "Candidate" : "Candidates"} Found
                        </h3>
                          <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                            {roleResult.consultants.map((consultant, index) => {
                              const consultantId = consultant.id || `consultant-${roleIndex}-${index}`;
                              const isDescriptionExpanded = expandedDescriptions.has(consultantId);
                              const isSkillsExpanded = expandedSkills.has(consultantId);
                              const hasManySkills = consultant.skills.length > 6;
                              const visibleSkills = hasManySkills && !isSkillsExpanded ? consultant.skills.slice(0, 6) : consultant.skills;
                              const experience = consultant.experience || "";
                              const hasLongExperience = experience.length > 150;
                              const truncatedExperience = hasLongExperience && !isDescriptionExpanded ? truncateAtSentence(experience) : experience;
                              
                              return (
                                <Card key={consultantId} className="transition-shadow hover:shadow-md">
                                  <CardHeader className="px-3 sm:px-6 pt-3 sm:pt-6 pb-2 sm:pb-4">
                                    <div className="flex items-start justify-between gap-2">
                                      <CardTitle className="text-base sm:text-lg md:text-xl font-semibold pr-2">{consultant.name}</CardTitle>
                                      <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
                                        {consultant.resumeId && (
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
                                        )}
                                        {consultant.matchScore !== undefined && (
                                          <MatchScoreBadge score={consultant.matchScore} />
                                        )}
                                      </div>
                                    </div>
                                    <CardDescription className="mt-2">
                                      <AvailabilityBadge availability={consultant.availability} variant="text" />
                                    </CardDescription>
                                  </CardHeader>
                                  <CardContent className="px-3 sm:px-6 pb-3 sm:pb-6">
                                    <div className="space-y-3">
                                      {experience && (
                                        <div>
                                          <p className="text-sm text-muted-foreground leading-relaxed">
                                            {truncatedExperience}
                                          </p>
                                          {hasLongExperience && (
                                            <Button
                                              variant="ghost"
                                              size="sm"
                                              onClick={() => toggleDescriptionExpanded(consultantId)}
                                              className="mt-1 h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                                            >
                                              {isDescriptionExpanded ? (
                                                <>
                                                  <ChevronUp className="h-3 w-3 mr-1" />
                                                  Show less
                                                </>
                                              ) : (
                                                <>
                                                  <ChevronDown className="h-3 w-3 mr-1" />
                                                  Show more
                                                </>
                                              )}
                                            </Button>
                                          )}
                                        </div>
                                      )}
                                      {hasManySkills ? (
                                        <div>
                                          <div className="flex items-center justify-between mb-2">
                                            <h3 className="text-sm font-medium text-muted-foreground">Skills</h3>
                                            <Button
                                              variant="ghost"
                                              size="sm"
                                              onClick={() => toggleSkillsExpanded(consultantId)}
                                              className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                                            >
                                              {isSkillsExpanded ? (
                                                <>
                                                  <ChevronUp className="h-3 w-3 mr-1" />
                                                  Show less
                                                </>
                                              ) : (
                                                <>
                                                  <ChevronDown className="h-3 w-3 mr-1" />
                                                  Show all ({consultant.skills.length})
                                                </>
                                              )}
                                            </Button>
                                          </div>
                                          <SkillTags skills={visibleSkills} />
                                        </div>
                                      ) : (
                                        <div>
                                          <h3 className="text-sm font-medium mb-2 text-muted-foreground">Skills</h3>
                                          <SkillTags skills={consultant.skills} />
                                        </div>
                                      )}
                                    </div>
                                  </CardContent>
                                </Card>
                              );
                            })}
                          </div>
                        </>
                    </div>
                  ))}
                </div>
                );
              })()
            ) : (
              // Legacy single query results
              consultants.length === 0 ? (
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex flex-col items-center justify-center py-12">
                      <Users className="h-12 w-12 text-muted-foreground mb-4" />
                      <p className="text-muted-foreground text-center text-lg font-semibold">
                        No consultants found.
                      </p>
                      <p className="text-muted-foreground text-center text-sm mt-2">
                        Try adjusting your project description or check back later.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <>
                  <div className="flex items-center justify-between flex-wrap gap-2 sm:gap-4">
                    <h2 className="text-lg sm:text-xl md:text-2xl font-semibold flex items-center gap-2">
                      <Users className="h-4 w-4 sm:h-5 sm:w-5 md:h-6 md:w-6" />
                      Found {consultants.length} {consultants.length === 1 ? "Consultant" : "Consultants"}
                    </h2>
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      Sorted by match score
                    </p>
                  </div>
                  <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                    {consultants.map((consultant, index) => {
                      const consultantId = consultant.id || `consultant-${index}`;
                      const isDescriptionExpanded = expandedDescriptions.has(consultantId);
                      const isSkillsExpanded = expandedSkills.has(consultantId);
                      const hasManySkills = consultant.skills.length > 6;
                      const visibleSkills = hasManySkills && !isSkillsExpanded ? consultant.skills.slice(0, 6) : consultant.skills;
                      const experience = consultant.experience || "";
                      const hasLongExperience = experience.length > 150;
                      const truncatedExperience = hasLongExperience && !isDescriptionExpanded ? truncateAtSentence(experience) : experience;
                      
                      return (
                        <Card key={consultantId} className="transition-shadow hover:shadow-md">
                          <CardHeader className="px-3 sm:px-6 pt-3 sm:pt-6 pb-2 sm:pb-4">
                            <div className="flex items-start justify-between gap-2">
                              <CardTitle className="text-base sm:text-lg md:text-xl font-semibold pr-2">{consultant.name}</CardTitle>
                              <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
                                {consultant.resumeId && (
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
                                )}
                                {consultant.matchScore !== undefined && (
                                  <MatchScoreBadge score={consultant.matchScore} />
                                )}
                              </div>
                            </div>
                            <CardDescription className="mt-2">
                              <AvailabilityBadge availability={consultant.availability} variant="text" />
                            </CardDescription>
                          </CardHeader>
                          <CardContent className="px-3 sm:px-6 pb-3 sm:pb-6">
                            <div className="space-y-3">
                              {experience && (
                                <div>
                                  <p className="text-sm text-muted-foreground leading-relaxed">
                                    {truncatedExperience}
                                  </p>
                                  {hasLongExperience && (
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => toggleDescriptionExpanded(consultantId)}
                                      className="mt-1 h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                                    >
                                      {isDescriptionExpanded ? (
                                        <>
                                          <ChevronUp className="h-3 w-3 mr-1" />
                                          Show less
                                        </>
                                      ) : (
                                        <>
                                          <ChevronDown className="h-3 w-3 mr-1" />
                                          Show more
                                        </>
                                      )}
                                    </Button>
                                  )}
                                </div>
                              )}
                              {hasManySkills ? (
                                <div>
                                  <div className="flex items-center justify-between mb-2">
                                    <h3 className="text-sm font-medium text-muted-foreground">Skills</h3>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => toggleSkillsExpanded(consultantId)}
                                      className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                                    >
                                      {isSkillsExpanded ? (
                                        <>
                                          <ChevronUp className="h-3 w-3 mr-1" />
                                          Show less
                                        </>
                                      ) : (
                                        <>
                                          <ChevronDown className="h-3 w-3 mr-1" />
                                          Show all ({consultant.skills.length})
                                        </>
                                      )}
                                    </Button>
                                  </div>
                                  <SkillTags skills={visibleSkills} />
                                </div>
                              ) : (
                                <div>
                                  <h3 className="text-sm font-medium mb-2 text-muted-foreground">Skills</h3>
                                  <SkillTags skills={consultant.skills} />
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                </>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

