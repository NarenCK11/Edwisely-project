import React, { useState } from "react";
import Modal from "./Modal.jsx";
import api from "../api/axios.js";

export default function AddJDModal({ isOpen, onClose, onCreated }) {
  const [tab, setTab] = useState("text");
  const [roleName, setRoleName] = useState("");
  const [company, setCompany] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const reset = () => {
    setRoleName("");
    setCompany("");
    setDescription("");
    setFile(null);
    setTab("text");
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      let res;
      if (tab === "file") {
        const formData = new FormData();
        formData.append("role_name", roleName);
        formData.append("company", company);
        if (file) formData.append("jd_file", file);
        res = await api.post("/api/jd", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } else {
        res = await api.post("/api/jd", {
          role_name: roleName,
          company,
          description,
        });
      }
      onCreated?.(res.data);
      reset();
      onClose();
    } catch (err) {
      const msg = err.response?.data?.error || "Failed to create job description";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} title="Add New Job Description" onClose={onClose}>
      <div className="mb-3 flex border-b border-slate-200 text-xs font-medium text-slate-600">
        <button
          type="button"
          onClick={() => setTab("text")}
          className={`px-3 py-2 border-b-2 ${
            tab === "text" ? "border-indigo-600 text-indigo-700" : "border-transparent"
          }`}
        >
          Type JD
        </button>
        <button
          type="button"
          onClick={() => setTab("file")}
          className={`px-3 py-2 border-b-2 ${
            tab === "file" ? "border-indigo-600 text-indigo-700" : "border-transparent"
          }`}
        >
          Upload PDF
        </button>
      </div>
      {error && (
        <div className="mb-3 text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1.5">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">
            Role Name
          </label>
          <input
            type="text"
            value={roleName}
            onChange={(e) => setRoleName(e.target.value)}
            required
            className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">
            Company
          </label>
          <input
            type="text"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            required
            className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        {tab === "text" ? (
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={5}
              required
              className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
        ) : (
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              JD PDF
            </label>
            <input
              type="file"
              accept=".pdf,.txt"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full text-xs"
            />
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 text-sm rounded-md border border-slate-300 text-slate-700 hover:bg-slate-50"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-3 py-1.5 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {loading ? "Saving..." : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

