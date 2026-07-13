export default function SkillChips({ skills }) {
  if (!skills || skills.length === 0) {
    return <span className="text-muted">—</span>;
  }

  return (
    <div className="skill-chips">
      {skills.map((skill) => (
        <span key={skill} className="skill-chip">
          {skill}
        </span>
      ))}
    </div>
  );
}
