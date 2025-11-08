import { Routes, Route } from "react-router-dom";
import { ProjectDescriptionPage } from "./pages/ProjectDescriptionPage";
import { ConsultantResultsPage } from "./pages/ConsultantResultsPage";
import "./index.css";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<ProjectDescriptionPage />} />
      <Route path="/results" element={<ConsultantResultsPage />} />
    </Routes>
  );
}

export default App;
