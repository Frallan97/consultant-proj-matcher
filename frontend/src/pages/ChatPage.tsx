import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChatInterface } from "@/components/ChatInterface";
import { FindMatchForm } from "@/components/FindMatchForm";
import { OverviewSkeleton } from "@/components/ui/LoadingSkeleton";
import { getOverview, type OverviewData } from "@/lib/api";
import { useEffect, useState } from "react";
import { Users, Search } from "lucide-react";

type Mode = "assemble" | "find";

export function ChatPage() {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [mode, setMode] = useState<Mode>("assemble");
  const navigate = useNavigate();

  useEffect(() => {
    const fetchOverview = async () => {
      setLoadingOverview(true);
      try {
        const data = await getOverview();
        setOverview(data);
      } catch (error) {
        console.error("Failed to fetch overview:", error);
        setOverview({ cvCount: 0, uniqueSkillsCount: 0, topSkills: [] });
      } finally {
        setLoadingOverview(false);
      }
    };
    fetchOverview();
  }, []);

  const handleComplete = (roles: any[]) => {
    navigate("/results", { state: { roles } });
  };

  const handleFindMatch = (description: string) => {
    navigate("/results", { state: { projectDescription: description } });
  };

  return (
    <div className="w-full bg-background overflow-x-hidden">
      <div className="container mx-auto px-3 sm:px-4 py-4 sm:py-8 md:py-16 max-w-6xl">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 items-stretch">
          <div className="lg:col-span-2">
            <Card className="h-[calc(100vh-180px)] sm:h-[600px] min-h-[500px] flex flex-col bg-card-primary">
              <CardHeader className="px-3 sm:px-6 pt-3 sm:pt-6 pb-2 sm:pb-4">
                <div className="flex flex-col items-center gap-3 sm:gap-4">
                  <div className="flex items-center gap-1 sm:gap-2 p-1 bg-muted/50 rounded-md border border-border/50 w-full sm:w-auto">
                    <Button
                      variant={mode === "assemble" ? "default" : "ghost"}
                      size="sm"
                      onClick={() => setMode("assemble")}
                      className="min-w-0 sm:min-w-[140px] flex-1 sm:flex-initial text-xs sm:text-sm px-2 sm:px-4"
                    >
                      <Users className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                      <span className="hidden sm:inline">Assemble a Team</span>
                      <span className="sm:hidden">Assemble</span>
                    </Button>
                    <Button
                      variant={mode === "find" ? "default" : "ghost"}
                      size="sm"
                      onClick={() => setMode("find")}
                      className="min-w-0 sm:min-w-[140px] flex-1 sm:flex-initial text-xs sm:text-sm px-2 sm:px-4"
                    >
                      <Search className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
                      <span className="hidden sm:inline">Find Match</span>
                      <span className="sm:hidden">Find</span>
                    </Button>
                  </div>
                  <CardTitle className="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-semibold text-center text-primary px-2">
                    {mode === "assemble" ? "Assemble Your Team" : "Find the Best Match"}
                  </CardTitle>
                  <p className="text-muted-foreground text-center mt-1 sm:mt-2 max-w-md text-xs sm:text-sm px-2">
                    {mode === "assemble"
                      ? "Chat with our AI assistant to find the perfect consultants for your project"
                      : "Enter a job description to find the best matching candidate for the role"}
                  </p>
                </div>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col overflow-hidden p-0">
                {mode === "assemble" ? (
                  <ChatInterface onComplete={handleComplete} />
                ) : (
                  <FindMatchForm onMatch={handleFindMatch} />
                )}
              </CardContent>
            </Card>
          </div>
          <div className="lg:col-span-1">
            {loadingOverview ? (
              <OverviewSkeleton />
            ) : (
              <Card className="h-auto lg:h-full flex flex-col bg-card-secondary">
                <CardHeader className="px-3 sm:px-6 pt-3 sm:pt-6 pb-2 sm:pb-4">
                  <CardTitle className="text-lg sm:text-xl font-semibold">Overview</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 sm:space-y-6 flex-1 px-3 sm:px-6 pb-3 sm:pb-6">
                  <div className="p-3 sm:p-4 rounded-md bg-primary/10 border border-primary/30">
                    <p className="text-xs sm:text-sm font-medium text-muted-foreground mb-1">Total CVs</p>
                    <p className="text-2xl sm:text-3xl font-semibold text-primary">
                      {overview?.cvCount ?? 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs sm:text-sm font-medium text-muted-foreground mb-2 sm:mb-3">Top 10 Skills</p>
                    {overview?.topSkills && overview.topSkills.length > 0 ? (
                      <div className="space-y-2 max-h-[300px] sm:max-h-[400px] overflow-y-auto">
                        {overview.topSkills.map((skillCount, index) => (
                          <div
                            key={index}
                            className="flex justify-between items-center p-2 rounded-md border border-border/50 hover:bg-accent/20 hover:border-accent/50 transition-colors"
                          >
                            <span className="text-xs sm:text-sm font-medium truncate pr-2">{skillCount.skill}</span>
                            <span className="text-xs sm:text-sm text-muted-foreground flex-shrink-0">
                              {skillCount.count} {skillCount.count === 1 ? "person" : "people"}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs sm:text-sm text-muted-foreground text-center py-4">No skills available</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

