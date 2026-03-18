import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../api/axios.js";
import TopScorerBanner from "../components/TopScorerBanner.jsx";
import AddCandidateModal from "../components/AddCandidateModal.jsx";
import SearchBar from "../components/SearchBar.jsx";
import CandidateCard from "../components/CandidateCard.jsx";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.jsx";

export default function JDDetail() {
  const { id } = useParams();
  const jdId = Number(id);
  const [jd, setJd] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loadingJD, setLoadingJD] = useState(true);
  const [loadingCandidates, setLoadingCandidates] = useState(true);
  const [error, setError] = useState("");
  const [showDesc, setShowDesc] = useState(false);
  const [showAddCandidate, setShowAddCandidate] = useState(false);
  const [search, setSearch] = useState("");
  const [evaluatingAll, setEvaluatingAll] = useState(false);
  const [evalLoadingId, setEvalLoadingId] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  useEffect(() => {
    const fetchJD = async () => {
      setLoadingJD(true);
      try {
        const res = await api.get(`/api/jd/${jdId}`);
        setJd(res.data);
      } catch (err) {
        const msg = err.response?.data?.error || "Failed to load job description";
        setError(msg);
      } finally {
        setLoadingJD(false);
      }
    };

    const fetchCandidates = async () => {
      setLoadingCandidates(true);
      try {
        const res = await api.get(`/api/jd/${jdId}/candidates`);
        setCandidates(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingCandidates(false);
      }
    };

    fetchJD();
    fetchCandidates();
  }, [jdId]);

  const filteredCandidates = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return candidates;
    return candidates.filter(
      (c) =>
        c.name.toLowerCase().includes(term) ||
        (c.email || "").toLowerCase().includes(term)
    );
  }, [candidates, search]);

  const topCandidate = useMemo(() => {
    const evaluated = candidates.filter((c) => c.is_evaluated && c.fit_score != null);
    if (!evaluated.length) return null;
    const best = [...evaluated].sort(
      (a, b) => (b.fit_score || 0) - (a.fit_score || 0)
    )[0];
    return candidates.find((c) => c.id === best.id) || null;
  }, [candidates]);

  const handleEvaluate = async (candidateId) => {
    setEvalLoadingId(candidateId);
    try {
      await api.post(`/api/jd/${jdId}/candidates/${candidateId}/evaluate`);
      const res = await api.get(`/api/jd/${jdId}/candidates/${candidateId}`);
      setCandidates((prev) =>
        prev.map((c) => (c.id === candidateId ? { ...c, ...res.data } : c))
      );
    } catch (err) {
      console.error("Evaluation failed", err);
    } finally {
      setEvalLoadingId(null);
    }
  };

  const handleEvaluateAll = async () => {
    setEvaluatingAll(true);
    try {
      await api.post(`/api/jd/${jdId}/candidates/evaluate-all`);
      const res = await api.get(`/api/jd/${jdId}/candidates`);
      setCandidates(res.data);
    } catch (err) {
      console.error("Evaluate all failed", err);
    } finally {
      setEvaluatingAll(false);
    }
  };

  const handleDeleteCandidate = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(
        `/api/jd/${jdId}/candidates/${deleteTarget.id}`
      );
      setCandidates((prev) => prev.filter((c) => c.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      console.error("Failed to delete candidate", err);
    }
  };

  const hasUnevaluated = candidates.some((c) => !c.is_evaluated);

  return (
    <div>
      {error && (
        <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      {loadingJD ? (
        <p className="text-sm text-slate-600">Loading job description...</p>
      ) : jd ? (
        <>
          <header className="mb-4">
            <h1 className="text-xl font-semibold text-slate-900">
              {jd.role_name}
            </h1>
            <p className="text-sm text-slate-600">
              {jd.company} •{" "}
              {jd.created_at
                ? `Created ${new Date(jd.created_at).toLocaleDateString()}`
                : ""}
            </p>
            <button
              type="button"
              className="mt-2 text-xs text-indigo-600 hover:text-indigo-700"
              onClick={() => setShowDesc((v) => !v)}
            >
              {showDesc ? "Hide job description" : "Show job description"}
            </button>
            {showDesc && (
              <div className="mt-2 max-h-64 overflow-auto rounded-md border border-slate-200 bg-white p-3 text-xs text-slate-800 whitespace-pre-wrap">
                {jd.description || "No description available."}
              </div>
            )}
          </header>

          <TopScorerBanner candidate={topCandidate} />

          <section className="mb-4 flex flex-wrap gap-3 items-center">
            <button
              type="button"
              onClick={() => setShowAddCandidate(true)}
              className="inline-flex items-center justify-center px-3 py-1.5 rounded-md bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700"
            >
              Add Candidate
            </button>
            <button
              type="button"
              onClick={handleEvaluateAll}
              disabled={evaluatingAll || !hasUnevaluated}
              className="inline-flex items-center justify-center px-3 py-1.5 rounded-md border text-xs font-medium border-slate-300 text-slate-800 hover:bg-slate-50 disabled:opacity-60"
            >
              {evaluatingAll ? "Evaluating..." : "Evaluate All"}
            </button>
            <div className="flex-1 min-w-[200px]">
              <SearchBar
                value={search}
                onChange={setSearch}
                placeholder="Search candidates by name or email"
              />
            </div>
          </section>

          {loadingCandidates ? (
            <p className="text-sm text-slate-600">Loading candidates...</p>
          ) : filteredCandidates.length === 0 ? (
            <div className="bg-white border border-dashed border-slate-300 rounded-lg p-6 text-center">
              <p className="text-sm font-medium text-slate-800 mb-1">
                No candidates yet
              </p>
              <p className="text-xs text-slate-600 mb-3">
                Upload the first resume to see AI-powered fit scores.
              </p>
              <button
                type="button"
                onClick={() => setShowAddCandidate(true)}
                className="inline-flex items-center justify-center px-3 py-1.5 rounded-md bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700"
              >
                Upload the first resume
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredCandidates.map((c, index) => (
                <CandidateCard
                  key={c.id}
                  candidate={c}
                  rank={index + 1}
                  loadingEvaluate={evalLoadingId === c.id}
                  onEvaluate={() => handleEvaluate(c.id)}
                  onReevaluate={() => handleEvaluate(c.id)}
                  onDelete={() => setDeleteTarget(c)}
                />
              ))}
            </div>
          )}
        </>
      ) : (
        <p className="text-sm text-slate-600">Job description not found.</p>
      )}

      <AddCandidateModal
        isOpen={showAddCandidate}
        onClose={() => setShowAddCandidate(false)}
        jdId={jdId}
        onCreated={() => {
          // refresh list on new candidate
          api.get(`/api/jd/${jdId}/candidates`).then((res) => setCandidates(res.data));
        }}
      />

      <ConfirmDeleteModal
        isOpen={!!deleteTarget}
        title="Delete candidate"
        message={
          deleteTarget
            ? `Delete candidate "${deleteTarget.name}"? This action cannot be undone.`
            : ""
        }
        onConfirm={handleDeleteCandidate}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

