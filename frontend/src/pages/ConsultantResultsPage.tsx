import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Consultant } from "@/types/consultant";
import { ArrowLeft, Loader2 } from "lucide-react";

const API_BASE_URL = "http://localhost:8000";

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

export function ConsultantResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const projectDescription = (location.state as { projectDescription?: string })?.projectDescription || "";
  
  const [consultants, setConsultants] = useState<Consultant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleBack = () => {
    navigate("/");
  };

  // Redirect to home if no project description (direct navigation)
  useEffect(() => {
    if (!projectDescription) {
      navigate("/", { replace: true });
    }
  }, [projectDescription, navigate]);

  // Fetch consultants from API
  useEffect(() => {
    if (!projectDescription) {
      return;
    }

    const fetchConsultants = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/consultants/match`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ projectDescription }),
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch consultants: ${response.statusText}`);
        }

        const data = await response.json();
        setConsultants(data.consultants || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch consultants");
        console.error("Error fetching consultants:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchConsultants();
  }, [projectDescription]);

  // Show nothing while redirecting
  if (!projectDescription) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8 md:py-16 max-w-6xl">
        <div className="space-y-6">
          {/* Header with back button */}
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="icon"
              onClick={handleBack}
              aria-label="Go back to project description"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-3xl md:text-4xl font-bold">Matching Consultants</h1>
          </div>

          {/* Project Description Display */}
          {projectDescription && (
            <Card className="shadow-md">
              <CardHeader>
                <CardTitle className="text-xl">Your Project Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground whitespace-pre-wrap">{projectDescription}</p>
              </CardContent>
            </Card>
          )}

          {/* Consultants List */}
          <div className="space-y-4">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="ml-3 text-muted-foreground">Loading consultants...</span>
              </div>
            ) : error ? (
              <Card className="shadow-md border-destructive">
                <CardContent className="pt-6">
                  <p className="text-destructive">Error: {error}</p>
                  <Button
                    onClick={() => window.location.reload()}
                    variant="outline"
                    className="mt-4"
                  >
                    Retry
                  </Button>
                </CardContent>
              </Card>
            ) : consultants.length === 0 ? (
              <Card className="shadow-md">
                <CardContent className="pt-6">
                  <p className="text-muted-foreground text-center py-8">
                    No consultants found. Try adjusting your project description.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-semibold">
                    Found {consultants.length} {consultants.length === 1 ? "Consultant" : "Consultants"}
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    Sorted by match score
                  </p>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {consultants.map((consultant, index) => (
                <Card key={consultant.id || `consultant-${index}`} className="shadow-md hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-xl">{consultant.name}</CardTitle>
                      {consultant.matchScore !== undefined && (
                        <span className="text-sm font-semibold text-primary">
                          {consultant.matchScore}% match
                        </span>
                      )}
                    </div>
                    <CardDescription>
                      <span className={getAvailabilityColor(consultant.availability)}>
                        {getAvailabilityLabel(consultant.availability)}
                      </span>
                      {consultant.experience && (
                        <span className="block mt-1 text-muted-foreground">
                          {consultant.experience}
                        </span>
                      )}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div>
                        <h3 className="text-sm font-medium mb-2">Skills</h3>
                        <div className="flex flex-wrap gap-2">
                          {consultant.skills.map((skill, index) => (
                            <span
                              key={index}
                              className="inline-flex items-center rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

