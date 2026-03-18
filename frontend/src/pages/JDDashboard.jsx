import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios.js";
import { useAuth } from "../context/AuthContext.jsx";
import JDCard from "../components/JDCard.jsx";
import AddJDModal from "../components/AddJDModal.jsx";
import ConfirmDeleteModal from "../components/ConfirmDeleteModal.jsx";

export default function JDDashboard() {
  const { hr } = useAuth();
  const [jds, setJds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const navigate = useNavigate();

  const fetchJDs = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/api/jd");
      setJds(res.data);
    } catch (err) {
      const msg = err.response?.data?.error || "Failed to load job descriptions";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJDs();
  }, []);

  const totalCandidates = jds.reduce(
    (acc, jd) => acc + (jd.total_candidates ?? 0),
    0
  );

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/api/jd/${deleteTarget.id}`);
      setJds((prev) => prev.filter((j) => j.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      // keep modal open; show basic error in console for now
      console.error("Failed to delete JD", err);
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div>
      <section className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            {hr ? `Welcome back, ${hr.name}` : "Job Descriptions"}
          </h1>
          <p className="text-sm text-slate-600">
            Manage your open roles and quickly see which candidates fit best.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center justify-center px-4 py-2 rounded-md bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
        >
          Add New Job Description
        </button>
      </section>

      <section className="mb-6 grid grid-cols-2 gap-4 text-sm">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <p className="text-xs text-slate-500 mb-1">Total Job Descriptions</p>
          <p className="text-2xl font-semibold text-slate-900">{jds.length}</p>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <p className="text-xs text-slate-500 mb-1">Total Candidates</p>
          <p className="text-2xl font-semibold text-slate-900">
            {totalCandidates}
          </p>
        </div>
      </section>

      {error && (
        <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-600">Loading job descriptions...</p>
      ) : jds.length === 0 ? (
        <div className="bg-white border border-dashed border-slate-300 rounded-lg p-6 text-center">
          <p className="text-sm font-medium text-slate-800 mb-1">
            No job descriptions yet
          </p>
          <p className="text-xs text-slate-600 mb-3">
            Add your first job description to start ranking candidates.
          </p>
          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center justify-center px-3 py-1.5 rounded-md bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700"
          >
            Add your first job description
          </button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {jds.map((jd) => (
            <JDCard
              key={jd.id}
              jd={jd}
              onClick={() => navigate(`/jd/${jd.id}`)}
              onDelete={() => setDeleteTarget(jd)}
            />
          ))}
        </div>
      )}

      <AddJDModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onCreated={(jd) => setJds((prev) => [jd, ...prev])}
      />

      <ConfirmDeleteModal
        isOpen={!!deleteTarget}
        title="Delete job description"
        message={
          deleteTarget
            ? `Delete "${deleteTarget.role_name}" at ${deleteTarget.company}? All associated candidates will also be removed.`
            : ""
        }
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        loading={deleteLoading}
      />
    </div>
  );
}

