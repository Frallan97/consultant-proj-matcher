import { cn } from "@/lib/utils";
import { Badge } from "./badge";

interface SkillTagsProps {
  skills: string[];
  maxVisible?: number;
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function SkillTags({ skills, maxVisible, className, size = "md" }: SkillTagsProps) {
  if (skills.length === 0) {
    return <span className="text-sm text-muted-foreground">No skills listed</span>;
  }

  const visibleSkills = maxVisible ? skills.slice(0, maxVisible) : skills;
  const remainingCount = maxVisible ? skills.length - maxVisible : 0;

  const sizeClasses = {
    sm: "text-xs px-1.5 py-0.5",
    md: "text-xs px-2 py-1",
    lg: "text-sm px-2.5 py-1",
  };

  return (
    <div className={cn("flex flex-wrap gap-1.5 sm:gap-2", className)}>
      {visibleSkills.map((skill, index) => (
        <Badge
          key={index}
          variant="secondary"
          className={cn(
            "bg-primary/10 text-primary hover:bg-primary/20 transition-colors",
            sizeClasses[size]
          )}
        >
          {skill}
        </Badge>
      ))}
      {remainingCount > 0 && (
        <Badge variant="outline" className={cn("text-muted-foreground", sizeClasses[size])}>
          +{remainingCount}
        </Badge>
      )}
    </div>
  );
}

