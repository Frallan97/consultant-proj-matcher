import { useState } from "react";
import { Button } from "@/components/ui/button";
import { FORM_CONSTANTS } from "@/lib/constants";
import { Loader2 } from "lucide-react";

interface FindMatchFormProps {
  onMatch: (description: string) => void;
}

export function FindMatchForm({ onMatch }: FindMatchFormProps) {
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);

  const characterCount = description.length;
  const maxCharacters = FORM_CONSTANTS.MAX_CHARACTERS;

  const handleSubmit = async () => {
    if (!description.trim() || characterCount > maxCharacters) return;
    
    setLoading(true);
    try {
      onMatch(description.trim());
    } catch (error) {
      console.error("Error submitting job description:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isNearLimit = characterCount > maxCharacters * FORM_CONSTANTS.CHARACTER_WARNING_THRESHOLD;
  const isOverLimit = characterCount > maxCharacters;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 p-2 sm:p-4 space-y-3 sm:space-y-4 flex flex-col min-h-0">
        <div className="flex-1 flex flex-col min-h-0">
          <label
            htmlFor="job-description"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 sr-only"
          >
            Job Description
          </label>
          <textarea
            id="job-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Enter the job description, role requirements, skills needed, and any other relevant details to find the best matching candidate..."
            className={`flex-1 w-full rounded-md border bg-background px-2 sm:px-3 py-2 text-sm sm:text-base font-normal shadow-sm transition-all file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/20 focus-visible:shadow-sm disabled:cursor-not-allowed disabled:opacity-50 resize-none ${
              isOverLimit
                ? "border-destructive/60 focus-visible:ring-destructive/20"
                : isNearLimit
                ? "border-accent/60 focus-visible:ring-accent/20"
                : "border-border/50 focus-visible:ring-ring/20"
            }`}
            aria-label="Job description input"
            maxLength={maxCharacters}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <div className="flex justify-between items-center text-xs mt-2 flex-shrink-0">
            <span className={isOverLimit ? "text-destructive font-medium" : "text-muted-foreground"}>
              {characterCount} / {maxCharacters} characters
            </span>
            {isNearLimit && !isOverLimit && (
              <span className="text-yellow-600 font-medium animate-in fade-in text-xs">
                Approaching limit
              </span>
            )}
            {isOverLimit && (
              <span className="text-destructive font-medium animate-in fade-in text-xs">
                Character limit exceeded
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="border-t border-border/50 bg-background p-2 sm:p-4 flex-shrink-0">
        <div className="flex justify-end gap-2">
          <Button
            onClick={handleSubmit}
            disabled={!description.trim() || isOverLimit || loading}
            size="lg"
            className="min-w-[100px] sm:min-w-[120px] text-xs sm:text-sm px-3 sm:px-4"
          >
            {loading ? (
              <>
                <Loader2 className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2 animate-spin" />
                <span className="hidden sm:inline">Finding Match...</span>
                <span className="sm:hidden">Finding...</span>
              </>
            ) : (
              "Find Match"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

