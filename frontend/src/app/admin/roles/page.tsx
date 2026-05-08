'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  Plus,
  Pencil,
  Trash2,
  ChevronRight,
  ArrowLeft,
  Shield,
  ShieldCheck,
  Layers3,
  Save,
  X,
  Copy,
} from 'lucide-react';
import Link from 'next/link';

type Designation = {
  id: string;
  title: string;
  description: string;
  team_hint: string;
  dept_hint: string;
  item_count: number;
};

type AccessItem = {
  id: string;
  designation_id: string;
  access_item: string;
  display_name: string;
  system: string;
  description: string;
  mandatory: number;
  owner_team: string;
  servicenow_catalog_item_id: string;
  sort_order: number;
};

type Options = {
  teams: string[];
  departments: string[];
  systems: string[];
  owner_teams: string[];
};

export default function AdminRolesPage() {
  const [designations, setDesignations] = useState<Designation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [items, setItems] = useState<AccessItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [showCopyRole, setShowCopyRole] = useState(false);
  const [editingRole, setEditingRole] = useState<Designation | null>(null);
  const [showItemWorkflow, setShowItemWorkflow] = useState(false);
  const [options, setOptions] = useState<Options>({ teams: [], departments: [], systems: [], owner_teams: [] });

  const fetchOptions = useCallback(async () => {
    const res = await fetch('/api/admin/options');
    const data = await res.json();
    setOptions(data);
  }, []);

  const fetchDesignations = useCallback(async () => {
    const res = await fetch('/api/admin/designations');
    const data = await res.json();
    setDesignations(data.designations ?? []);
    setLoading(false);
  }, []);

  const fetchItems = useCallback(async (id: string) => {
    const res = await fetch(`/api/admin/designations/${id}/items`);
    const data = await res.json();
    setItems(data.items ?? []);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchDesignations();
    fetchOptions();
  }, [fetchDesignations, fetchOptions]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (selectedId) fetchItems(selectedId);
  }, [selectedId, fetchItems]);

  const deleteDesignation = async (id: string) => {
    if (!confirm(`Delete role "${id}" and all its access items?`)) return;
    await fetch(`/api/admin/designations/${id}`, { method: 'DELETE' });
    setSelectedId(null);
    setItems([]);
    fetchDesignations();
  };


  const selected = designations.find((d) => d.id === selectedId);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex items-center gap-2 text-gray-500 hover:text-gray-900 transition-colors text-sm"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Chat
            </Link>
            <div className="h-5 w-px bg-gray-200" />
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
                <Layers3 className="w-4 h-4 text-amber-700" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900 leading-tight">Role Configuration</h1>
                <p className="text-xs text-gray-500">Manage designations and access templates</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCopyRole(true)}
              className="flex items-center gap-2 bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 font-medium py-2 px-4 rounded-lg transition-colors text-sm"
            >
              <Copy className="w-4 h-4" />
              Copy Role ID
            </button>
            <button
              onClick={() => setShowCreateRole(true)}
              className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white font-medium py-2 px-4 rounded-lg transition-colors text-sm"
            >
              <Plus className="w-4 h-4" />
              New Role
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex gap-6">
          {/* Left: Roles list */}
          <div className="w-80 flex-shrink-0">
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100">
                <h2 className="text-sm font-semibold text-gray-700">
                  Roles ({designations.length})
                </h2>
              </div>
              {loading ? (
                <div className="p-6 text-center text-gray-400 text-sm">Loading...</div>
              ) : designations.length === 0 ? (
                <div className="p-6 text-center text-gray-400 text-sm">
                  No roles configured yet
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {designations.map((d) => (
                    <button
                      key={d.id}
                      onClick={() => setSelectedId(d.id)}
                      className={[
                        'w-full text-left px-4 py-3 flex items-center gap-3 transition-colors',
                        selectedId === d.id
                          ? 'bg-amber-50 border-l-3 border-l-amber-500'
                          : 'hover:bg-gray-50',
                      ].join(' ')}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {d.title}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {d.item_count} access items
                          {d.team_hint ? ` · ${d.team_hint}` : ''}
                        </p>
                      </div>
                      <ChevronRight className="w-4 h-4 text-gray-300 flex-shrink-0" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right: Role detail + items */}
          <div className="flex-1 min-w-0">
            {!selected ? (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <Layers3 className="w-12 h-12 text-gray-200 mx-auto mb-4" />
                <p className="text-gray-500 text-sm">
                  Select a role from the left to view and manage its access items
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Role header card */}
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <h2 className="text-lg font-bold text-gray-900">{selected.title}</h2>
                      <p className="text-sm text-gray-500 mt-1">
                        {selected.description || 'No description'}
                      </p>
                      <div className="flex gap-4 mt-3">
                        {selected.team_hint && (
                          <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                            Team: {selected.team_hint}
                          </span>
                        )}
                        {selected.dept_hint && (
                          <span className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded">
                            Dept: {selected.dept_hint}
                          </span>
                        )}
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                          ID: {selected.id}
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setEditingRole(selected)}
                        className="p-2 rounded-lg border border-gray-200 text-gray-500 hover:text-amber-600 hover:border-amber-200 transition-colors"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => deleteDesignation(selected.id)}
                        className="p-2 rounded-lg border border-gray-200 text-gray-500 hover:text-red-600 hover:border-red-200 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Access items */}
                <div className="bg-white rounded-xl border border-gray-200">
                  <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-gray-700">
                      Access Items ({items.length})
                    </h3>
                    <button
                      onClick={() => setShowItemWorkflow(true)}
                      className="flex items-center gap-1.5 text-xs font-medium bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg transition-colors"
                    >
                      <Pencil className="w-3 h-3" />
                      Edit Items
                    </button>
                  </div>

                  {items.length === 0 ? (
                    <div className="p-8 text-center">
                      <Shield className="w-10 h-10 text-gray-200 mx-auto mb-3" />
                      <p className="text-gray-400 text-sm mb-3">
                        No access items configured for this role
                      </p>
                      <button
                        onClick={() => setShowItemWorkflow(true)}
                        className="text-xs font-medium text-amber-600 hover:text-amber-700"
                      >
                        + Add access items
                      </button>
                    </div>
                  ) : (
                    <div className="divide-y divide-gray-50">
                      {items.map((item) => (
                        <div
                          key={item.id}
                          className="px-5 py-3 flex items-center gap-4"
                        >
                          <div className="flex-shrink-0">
                            {item.mandatory ? (
                              <ShieldCheck className="w-5 h-5 text-green-600" />
                            ) : (
                              <Shield className="w-5 h-5 text-gray-400" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium text-gray-900">
                                {item.display_name || item.access_item}
                              </p>
                              <span
                                className={[
                                  'text-[10px] px-1.5 py-0.5 rounded font-medium',
                                  item.mandatory
                                    ? 'bg-green-50 text-green-700'
                                    : 'bg-gray-100 text-gray-500',
                                ].join(' ')}
                              >
                                {item.mandatory ? 'Mandatory' : 'Optional'}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 mt-0.5">
                              {item.system}
                              {item.owner_team ? ` · ${item.owner_team}` : ''}
                              {item.description ? ` — ${item.description}` : ''}
                            </p>
                          </div>
                          <span className="text-[10px] text-gray-300">#{item.sort_order}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Role Modal */}
      {showCreateRole && (
        <CreateRoleModal
          options={options}
          onClose={() => setShowCreateRole(false)}
          onCreated={() => {
            setShowCreateRole(false);
            fetchDesignations();
            fetchOptions();
          }}
        />
      )}

      {/* Copy Role Modal */}
      {showCopyRole && (
        <CopyRoleModal
          designations={designations}
          onClose={() => setShowCopyRole(false)}
          onCopied={(id) => {
            setShowCopyRole(false);
            fetchDesignations();
            fetchOptions();
            setSelectedId(id);
          }}
        />
      )}

      {/* Edit Role Modal */}
      {editingRole && (
        <EditRoleModal
          role={editingRole}
          options={options}
          onClose={() => setEditingRole(null)}
          onSaved={() => {
            setEditingRole(null);
            fetchDesignations();
            fetchOptions();
          }}
        />
      )}

      {/* Item Workflow Editor */}
      {showItemWorkflow && selectedId && (
        <ItemWorkflowEditor
          designationId={selectedId}
          existingItems={items}
          options={options}
          onClose={() => setShowItemWorkflow(false)}
          onSaved={() => {
            setShowItemWorkflow(false);
            fetchItems(selectedId);
            fetchDesignations();
            fetchOptions();
          }}
        />
      )}
    </div>
  );
}

// ── Modals ──────────────────────────────────────────────────────────────────

function CreateRoleModal({
  options,
  onClose,
  onCreated,
}: {
  options: Options;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    id: '',
    title: '',
    description: '',
    team_hint: '',
    dept_hint: '',
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const res = await fetch('/api/admin/designations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    if (res.ok) onCreated();
    else alert('Failed to create role');
    setSaving(false);
  };

  return (
    <Modal title="Create New Role" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Role ID (snake_case)" required>
          <input
            type="text"
            value={form.id}
            onChange={(e) => setForm({ ...form, id: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
            placeholder="e.g. security_analyst"
            className="input"
            required
          />
        </Field>
        <Field label="Title" required>
          <input
            type="text"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="e.g. Security Analyst"
            className="input"
            required
          />
        </Field>
        <Field label="Description">
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Brief description of this role"
            className="input"
            rows={2}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Team">
            <SelectOrCustom
              options={options.teams}
              value={form.team_hint}
              onChange={(v) => setForm({ ...form, team_hint: v })}
              placeholder="Select or type a team"
            />
          </Field>
          <Field label="Department">
            <SelectOrCustom
              options={options.departments}
              value={form.dept_hint}
              onChange={(v) => setForm({ ...form, dept_hint: v })}
              placeholder="Select or type a department"
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button type="submit" disabled={saving} className="btn-primary">
            <Save className="w-4 h-4" />
            {saving ? 'Creating...' : 'Create Role'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function CopyRoleModal({
  designations,
  onClose,
  onCopied,
}: {
  designations: Designation[];
  onClose: () => void;
  onCopied: (id: string) => void;
}) {
  const [sourceId, setSourceId] = useState(designations[0]?.id ?? '');
  const source = designations.find((d) => d.id === sourceId);
  const [form, setForm] = useState({
    id: source ? `${source.id}_copy` : '',
    title: source ? `${source.title} Copy` : '',
    description: source?.description ?? '',
    team_hint: source?.team_hint ?? '',
    dept_hint: source?.dept_hint ?? '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const changeSource = (id: string) => {
    const next = designations.find((d) => d.id === id);
    setSourceId(id);
    if (next) {
      setForm({
        id: `${next.id}_copy`,
        title: `${next.title} Copy`,
        description: next.description ?? '',
        team_hint: next.team_hint ?? '',
        dept_hint: next.dept_hint ?? '',
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceId) return;
    setSaving(true);
    setError('');
    const res = await fetch('/api/admin/designations/copy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_designation_id: sourceId,
        ...form,
      }),
    });
    const data = await res.json();
    setSaving(false);
    if (res.ok) {
      onCopied(data.id);
    } else {
      setError(data.detail ?? data.error ?? 'Failed to copy role');
    }
  };

  return (
    <Modal title="Copy Role ID" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Source Role
          </label>
          <select
            value={sourceId}
            onChange={(e) => changeSource(e.target.value)}
            className="input"
            required
          >
            {designations.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title} ({d.id})
              </option>
            ))}
          </select>
          {source && (
            <p className="text-[11px] text-gray-400 mt-1">
              Copies the full access item bundle from {source.item_count} item{source.item_count !== 1 ? 's' : ''}.
            </p>
          )}
        </div>

        <Field label="New Role ID" required>
          <input
            required
            value={form.id}
            onChange={(e) => setForm({ ...form, id: e.target.value })}
            className="input"
            placeholder="devops_cloud_engineer_copy"
          />
        </Field>

        <Field label="New Role Title" required>
          <input
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="input"
            placeholder="DevOps / Cloud Engineer Copy"
          />
        </Field>

        <Field label="Description">
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="input min-h-20"
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Team Hint">
            <input
              value={form.team_hint}
              onChange={(e) => setForm({ ...form, team_hint: e.target.value })}
              className="input"
            />
          </Field>
          <Field label="Department Hint">
            <input
              value={form.dept_hint}
              onChange={(e) => setForm({ ...form, dept_hint: e.target.value })}
              className="input"
            />
          </Field>
        </div>

        {error && (
          <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button type="submit" disabled={saving} className="btn-primary">
            <Copy className="w-4 h-4" />
            {saving ? 'Copying...' : 'Copy Bundle'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function EditRoleModal({
  role,
  options,
  onClose,
  onSaved,
}: {
  role: Designation;
  options: Options;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    title: role.title,
    description: role.description,
    team_hint: role.team_hint,
    dept_hint: role.dept_hint,
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    const res = await fetch(`/api/admin/designations/${role.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    if (res.ok) onSaved();
    else alert('Failed to update role');
    setSaving(false);
  };

  return (
    <Modal title={`Edit: ${role.title}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Title" required>
          <input
            type="text"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="input"
            required
          />
        </Field>
        <Field label="Description">
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="input"
            rows={2}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Team">
            <SelectOrCustom
              options={options.teams}
              value={form.team_hint}
              onChange={(v) => setForm({ ...form, team_hint: v })}
              placeholder="Select or type a team"
            />
          </Field>
          <Field label="Department">
            <SelectOrCustom
              options={options.departments}
              value={form.dept_hint}
              onChange={(v) => setForm({ ...form, dept_hint: v })}
              placeholder="Select or type a department"
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button type="submit" disabled={saving} className="btn-primary">
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

type WorkflowRow = {
  _key: string;
  _isNew: boolean;
  _existingId?: string;
  access_item: string;
  display_name: string;
  system: string;
  description: string;
  mandatory: boolean;
  owner_team: string;
  servicenow_catalog_item_id: string;
  sort_order: number;
};

let _rowKeyCounter = 0;
function nextKey() {
  return `row_${++_rowKeyCounter}`;
}

function ItemWorkflowEditor({
  designationId,
  existingItems,
  options,
  onClose,
  onSaved,
}: {
  designationId: string;
  existingItems: AccessItem[];
  options: Options;
  onClose: () => void;
  onSaved: () => void;
}) {
  function emptyRow(order = 0): WorkflowRow {
    return {
      _key: nextKey(),
      _isNew: true,
      access_item: '',
      display_name: '',
      system: '',
      description: '',
      mandatory: false,
      owner_team: '',
      servicenow_catalog_item_id: '',
      sort_order: order,
    };
  }

  const [rows, setRows] = useState<WorkflowRow[]>(() =>
    existingItems.length > 0
      ? existingItems.map((item) => ({
          _key: nextKey(),
          _isNew: false,
          _existingId: item.id,
          access_item: item.access_item,
          display_name: item.display_name,
          system: item.system,
          description: item.description,
          mandatory: !!item.mandatory,
          owner_team: item.owner_team,
          servicenow_catalog_item_id: item.servicenow_catalog_item_id,
          sort_order: item.sort_order,
        }))
      : [emptyRow(0)]
  );
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState('');

  const addRow = () => {
    setRows([...rows, emptyRow(rows.length)]);
  };

  const removeRow = (key: string) => {
    setRows(rows.filter((r) => r._key !== key));
  };

  const updateRow = (key: string, field: string, value: string | boolean | number) => {
    setRows(rows.map((r) => (r._key === key ? { ...r, [field]: value } : r)));
  };

  const moveRow = (idx: number, dir: -1 | 1) => {
    const target = idx + dir;
    if (target < 0 || target >= rows.length) return;
    const newRows = [...rows];
    [newRows[idx], newRows[target]] = [newRows[target], newRows[idx]];
    setRows(newRows.map((r, i) => ({ ...r, sort_order: i })));
  };

  const handleSaveAll = async () => {
    const validRows = rows.filter((r) => r.access_item.trim());
    if (validRows.length === 0) {
      alert('Add at least one item with an Access Item ID');
      return;
    }

    setSaving(true);
    setStatus('Deleting old items...');

    // Delete all existing items first
    for (const item of existingItems) {
      await fetch(`/api/admin/items/${item.id}`, { method: 'DELETE' });
    }

    // Create all rows in order
    let created = 0;
    for (let i = 0; i < validRows.length; i++) {
      const row = validRows[i];
      setStatus(`Saving item ${i + 1} of ${validRows.length}...`);
      const res = await fetch(`/api/admin/designations/${designationId}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          access_item: row.access_item,
          display_name: row.display_name,
          system: row.system,
          description: row.description,
          mandatory: row.mandatory,
          owner_team: row.owner_team,
          servicenow_catalog_item_id: row.servicenow_catalog_item_id,
          sort_order: i,
        }),
      });
      if (res.ok) created++;
    }

    setStatus(`Done! ${created} items saved.`);
    setSaving(false);
    setTimeout(onSaved, 500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-5xl mx-4 max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Access Items Workflow</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Add, edit, reorder, and remove items. Click &quot;Save All&quot; when done.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto px-6 py-4">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-100">
                <th className="pb-2 pr-2 w-8">#</th>
                <th className="pb-2 pr-2">Access Item ID *</th>
                <th className="pb-2 pr-2">Display Name</th>
                <th className="pb-2 pr-2">System</th>
                <th className="pb-2 pr-2">Owner Team</th>
                <th className="pb-2 pr-2">Description</th>
                <th className="pb-2 pr-2 w-20 text-center">Mandatory</th>
                <th className="pb-2 w-24 text-center">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={row._key} className="border-b border-gray-50 hover:bg-amber-50/30">
                  <td className="py-2 pr-2 text-gray-400 font-mono">{idx + 1}</td>
                  <td className="py-2 pr-2">
                    <input
                      type="text"
                      value={row.access_item}
                      onChange={(e) => updateRow(row._key, 'access_item', e.target.value)}
                      placeholder="aws_console"
                      className="input py-1 px-2 text-xs"
                    />
                  </td>
                  <td className="py-2 pr-2">
                    <input
                      type="text"
                      value={row.display_name}
                      onChange={(e) => updateRow(row._key, 'display_name', e.target.value)}
                      placeholder="AWS Console Access"
                      className="input py-1 px-2 text-xs"
                    />
                  </td>
                  <td className="py-2 pr-2">
                    <select
                      value={row.system}
                      onChange={(e) => updateRow(row._key, 'system', e.target.value)}
                      className="input py-1 px-2 text-xs"
                    >
                      <option value="">-- System --</option>
                      {options.systems.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 pr-2">
                    <select
                      value={row.owner_team}
                      onChange={(e) => updateRow(row._key, 'owner_team', e.target.value)}
                      className="input py-1 px-2 text-xs"
                    >
                      <option value="">-- Owner --</option>
                      {options.owner_teams.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 pr-2">
                    <input
                      type="text"
                      value={row.description}
                      onChange={(e) => updateRow(row._key, 'description', e.target.value)}
                      placeholder="What this grants"
                      className="input py-1 px-2 text-xs"
                    />
                  </td>
                  <td className="py-2 pr-2 text-center">
                    <input
                      type="checkbox"
                      checked={row.mandatory}
                      onChange={(e) => updateRow(row._key, 'mandatory', e.target.checked)}
                      className="w-4 h-4 rounded border-gray-300 text-amber-500 focus:ring-amber-500"
                    />
                  </td>
                  <td className="py-2 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        type="button"
                        onClick={() => moveRow(idx, -1)}
                        disabled={idx === 0}
                        className="p-1 rounded text-gray-400 hover:text-gray-700 disabled:opacity-30"
                        title="Move up"
                      >
                        &#9650;
                      </button>
                      <button
                        type="button"
                        onClick={() => moveRow(idx, 1)}
                        disabled={idx === rows.length - 1}
                        className="p-1 rounded text-gray-400 hover:text-gray-700 disabled:opacity-30"
                        title="Move down"
                      >
                        &#9660;
                      </button>
                      <button
                        type="button"
                        onClick={() => removeRow(row._key)}
                        className="p-1 rounded text-gray-400 hover:text-red-600"
                        title="Remove"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <button
            type="button"
            onClick={addRow}
            className="mt-3 flex items-center gap-1.5 text-xs font-medium text-amber-600 hover:text-amber-700 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Row
          </button>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-gray-50 rounded-b-2xl">
          <div className="text-xs text-gray-500">
            {status || `${rows.filter((r) => r.access_item.trim()).length} item(s) ready`}
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="btn-secondary" disabled={saving}>
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSaveAll}
              disabled={saving}
              className="btn-primary"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save All'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Shared UI Components ────────────────────────────────────────────────────

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

function SelectOrCustom({
  options,
  value,
  onChange,
  placeholder,
}: {
  options: string[];
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  const [isCustom, setIsCustom] = useState(!options.includes(value) && value !== '');

  if (isCustom) {
    return (
      <div className="flex gap-1">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="input flex-1"
        />
        <button
          type="button"
          onClick={() => { setIsCustom(false); onChange(''); }}
          className="px-2 text-xs text-gray-500 hover:text-amber-600 border border-gray-200 rounded-lg"
          title="Switch to dropdown"
        >
          List
        </button>
      </div>
    );
  }

  return (
    <div className="flex gap-1">
      <select
        value={value}
        onChange={(e) => {
          if (e.target.value === '__custom__') {
            setIsCustom(true);
            onChange('');
          } else {
            onChange(e.target.value);
          }
        }}
        className="input flex-1 appearance-none"
      >
        <option value="">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
        <option value="__custom__">+ Custom value...</option>
      </select>
    </div>
  );
}
