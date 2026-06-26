/**
 * Campus AI - Teacher Gradebook.
 *
 * Place this file at: src/app/dashboard/gradebook/page.tsx
 *
 * Two tabs:
 *   - Subjects: create a subject (department + name + code + credits + semester)
 *     and browse the existing subject list.
 *   - Enter Marks: pick a subject, pick a section roster -> student, enter the
 *     marks, and save. The grade point is derived on the backend. Below the
 *     form you can see all results already recorded for the chosen subject.
 *
 * Backend endpoints:
 *   GET  /admin/departments                  -> [{ id, name, code }]
 *   GET  /admin/departments/{id}/sections     -> [{ id, name, year, department_id }]
 *   GET  /people/students?section_id={id}     -> [{ id, full_name, email, role, ... }]
 *   GET  /academics/subjects                  -> [{ id, name, code, credits, semester, department_id }]
 *   POST /academics/subjects                  body SubjectCreate
 *   POST /academics/results                   body { student_id, subject_id, marks_obtained, max_marks }
 *   GET  /academics/subjects/{id}/results      -> [{ id, student_id, subject_id, marks_obtained, max_marks, grade_point }]
 */

"use client"

import { useCallback, useEffect, useState } from "react"
import { api, ApiError } from "@/lib/api"

type Department = { id: number; name: string; code: string }
type Section = {
	id: number
	name: string
	year: number | null
	department_id: number
}
type Student = { id: number; full_name: string; email: string }
type Subject = {
	id: number
	name: string
	code: string
	credits: number
	semester: number
	department_id: number
}
type Result = {
	id: number
	student_id: number
	subject_id: number
	marks_obtained: number
	max_marks: number
	grade_point: number
}

function gradeColor(gp: number): string {
	if (gp >= 8) return "text-emerald-300"
	if (gp >= 6) return "text-amber-300"
	return "text-red-300"
}

const inputClass =
	"mt-1 w-full rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-indigo-400"

export default function GradebookPage() {
	const [tab, setTab] = useState<"subjects" | "marks">("subjects")
	const [departments, setDepartments] = useState<Department[]>([])
	const [subjects, setSubjects] = useState<Subject[]>([])
	const [studentNames, setStudentNames] = useState<Record<number, string>>({})

	const loadSubjects = useCallback(async () => {
		try {
			setSubjects(await api.get<Subject[]>("/academics/subjects"))
		} catch {
			// surfaced by the active tab when relevant
		}
	}, [])

	useEffect(() => {
		api
			.get<Department[]>("/admin/departments")
			.then(setDepartments)
			.catch(() => undefined)
		loadSubjects()
	}, [loadSubjects])

	function rememberNames(students: Student[]) {
		setStudentNames((prev) => {
			const next = { ...prev }
			for (const s of students) next[s.id] = s.full_name
			return next
		})
	}

	const tabClass = (active: boolean) =>
		`rounded-lg px-4 py-2 text-sm transition ${
			active ? "bg-indigo-500/15 text-white" : "text-slate-300 hover:bg-white/5"
		}`

	return (
		<div>
			<h2 className="text-2xl font-bold">Gradebook</h2>
			<p className="mt-1 text-sm text-slate-400">
				Manage subjects and record student marks. Grade points are derived
				automatically from the percentage.
			</p>

			<div className="mt-6 flex gap-2">
				<button
					onClick={() => setTab("subjects")}
					className={tabClass(tab === "subjects")}
				>
					Subjects
				</button>
				<button
					onClick={() => setTab("marks")}
					className={tabClass(tab === "marks")}
				>
					Enter Marks
				</button>
			</div>

			{tab === "subjects" ? (
				<SubjectsTab
					departments={departments}
					subjects={subjects}
					onCreated={loadSubjects}
				/>
			) : (
				<MarksTab
					departments={departments}
					subjects={subjects}
					studentNames={studentNames}
					rememberNames={rememberNames}
				/>
			)}
		</div>
	)
}

/* ------------------------------ Subjects tab ------------------------------ */

function SubjectsTab({
	departments,
	subjects,
	onCreated,
}: {
	departments: Department[]
	subjects: Subject[]
	onCreated: () => void
}) {
	const [deptId, setDeptId] = useState<string>("")
	const [name, setName] = useState("")
	const [code, setCode] = useState("")
	const [credits, setCredits] = useState("3")
	const [semester, setSemester] = useState("1")
	const [saving, setSaving] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [success, setSuccess] = useState<string | null>(null)

	async function create() {
		if (!deptId || !name.trim() || !code.trim()) {
			setError("Department, name and code are required.")
			return
		}
		setSaving(true)
		setError(null)
		setSuccess(null)
		try {
			const payload = {
				department_id: Number(deptId),
				name: name.trim(),
				code: code.trim(),
				credits: Number(credits),
				semester: Number(semester),
			}
			await api.post("/academics/subjects", payload)
			setSuccess(`Subject "${name.trim()}" added.`)
			setName("")
			setCode("")
			onCreated()
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not create subject.",
			)
		} finally {
			setSaving(false)
		}
	}

	const deptName = (id: number) =>
		departments.find((d) => d.id === id)?.code ?? `Dept #${id}`

	return (
		<div className="mt-6">
			{/* Create form */}
			<div className="rounded-2xl border border-white/10 bg-white/5 p-6">
				<h3 className="text-lg font-semibold">Add a subject</h3>
				<div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
					<div className="lg:col-span-1">
						<label className="text-sm text-slate-400">Department</label>
						<select
							value={deptId}
							onChange={(e) => setDeptId(e.target.value)}
							className={inputClass}
						>
							<option value="">Select department</option>
							{departments.map((d) => (
								<option key={d.id} value={d.id}>
									{d.name} ({d.code})
								</option>
							))}
						</select>
					</div>
					<div>
						<label className="text-sm text-slate-400">Subject name</label>
						<input
							value={name}
							onChange={(e) => setName(e.target.value)}
							className={inputClass}
							placeholder="Data Structures"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-400">Code</label>
						<input
							value={code}
							onChange={(e) => setCode(e.target.value)}
							className={inputClass}
							placeholder="CS201"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-400">Credits (1-10)</label>
						<input
							type="number"
							min={1}
							max={10}
							value={credits}
							onChange={(e) => setCredits(e.target.value)}
							className={inputClass}
						/>
					</div>
					<div>
						<label className="text-sm text-slate-400">Semester (1-12)</label>
						<input
							type="number"
							min={1}
							max={12}
							value={semester}
							onChange={(e) => setSemester(e.target.value)}
							className={inputClass}
						/>
					</div>
				</div>

				{error && (
					<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
						{error}
					</p>
				)}
				{success && (
					<p className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
						{success}
					</p>
				)}

				<button
					onClick={create}
					disabled={saving}
					className="mt-4 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
				>
					{saving ? "Adding..." : "Add subject"}
				</button>
			</div>

			{/* List */}
			<div className="mt-8">
				<h3 className="text-lg font-semibold">All subjects</h3>
				{subjects.length === 0 ? (
					<p className="mt-3 text-slate-400">No subjects yet.</p>
				) : (
					<div className="mt-3 space-y-2">
						{subjects.map((s) => (
							<div
								key={s.id}
								className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3"
							>
								<div>
									<p className="font-medium">
										{s.name}{" "}
										<span className="text-xs text-slate-500">({s.code})</span>
									</p>
									<p className="text-xs text-slate-500">
										{deptName(s.department_id)} - Sem {s.semester} - {s.credits}{" "}
										credits
									</p>
								</div>
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	)
}

/* ------------------------------- Marks tab ------------------------------- */

function MarksTab({
	departments,
	subjects,
	studentNames,
	rememberNames,
}: {
	departments: Department[]
	subjects: Subject[]
	studentNames: Record<number, string>
	rememberNames: (students: Student[]) => void
}) {
	const [subjectId, setSubjectId] = useState<string>("")
	const [deptId, setDeptId] = useState<string>("")
	const [sectionId, setSectionId] = useState<string>("")
	const [studentId, setStudentId] = useState<string>("")
	const [marks, setMarks] = useState("")
	const [maxMarks, setMaxMarks] = useState("100")

	const [sections, setSections] = useState<Section[]>([])
	const [roster, setRoster] = useState<Student[]>([])
	const [results, setResults] = useState<Result[]>([])

	const [saving, setSaving] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [success, setSuccess] = useState<string | null>(null)

	// Load sections when department changes.
	useEffect(() => {
		setSections([])
		setSectionId("")
		setRoster([])
		setStudentId("")
		if (!deptId) return
		api
			.get<Section[]>(`/admin/departments/${deptId}/sections`)
			.then(setSections)
			.catch(() => undefined)
	}, [deptId])

	// Load roster when section changes.
	useEffect(() => {
		setRoster([])
		setStudentId("")
		if (!sectionId) return
		api
			.get<Student[]>(`/people/students?section_id=${sectionId}`)
			.then((students) => {
				setRoster(students)
				rememberNames(students)
			})
			.catch(() => undefined)
	}, [sectionId, rememberNames])

	const loadResults = useCallback(async (subId: string) => {
		if (!subId) {
			setResults([])
			return
		}
		try {
			setResults(
				await api.get<Result[]>(`/academics/subjects/${subId}/results`),
			)
		} catch {
			setResults([])
		}
	}, [])

	// Reload results when subject changes.
	useEffect(() => {
		loadResults(subjectId)
	}, [subjectId, loadResults])

	async function save() {
		if (!subjectId || !studentId || !marks) {
			setError("Subject, student and marks are required.")
			return
		}
		setSaving(true)
		setError(null)
		setSuccess(null)
		try {
			const payload = {
				student_id: Number(studentId),
				subject_id: Number(subjectId),
				marks_obtained: Number(marks),
				max_marks: Number(maxMarks) || 100,
			}
			await api.post("/academics/results", payload)
			setSuccess("Marks saved.")
			setMarks("")
			await loadResults(subjectId)
		} catch (err) {
			setError(
				err instanceof ApiError ? err.message : "Could not save marks.",
			)
		} finally {
			setSaving(false)
		}
	}

	const nameFor = (id: number) => studentNames[id] ?? `Student #${id}`

	return (
		<div className="mt-6">
			<div className="rounded-2xl border border-white/10 bg-white/5 p-6">
				<h3 className="text-lg font-semibold">Record marks</h3>

				<div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
					<div>
						<label className="text-sm text-slate-400">Subject</label>
						<select
							value={subjectId}
							onChange={(e) => setSubjectId(e.target.value)}
							className={inputClass}
						>
							<option value="">Select subject</option>
							{subjects.map((s) => (
								<option key={s.id} value={s.id}>
									{s.name} ({s.code}) - Sem {s.semester}
								</option>
							))}
						</select>
					</div>
					<div>
						<label className="text-sm text-slate-400">Department</label>
						<select
							value={deptId}
							onChange={(e) => setDeptId(e.target.value)}
							className={inputClass}
						>
							<option value="">Select department</option>
							{departments.map((d) => (
								<option key={d.id} value={d.id}>
									{d.name} ({d.code})
								</option>
							))}
						</select>
					</div>
					<div>
						<label className="text-sm text-slate-400">Section</label>
						<select
							value={sectionId}
							onChange={(e) => setSectionId(e.target.value)}
							disabled={!deptId}
							className={inputClass}
						>
							<option value="">Select section</option>
							{sections.map((s) => (
								<option key={s.id} value={s.id}>
									{s.name}
									{s.year ? ` - Year ${s.year}` : ""}
								</option>
							))}
						</select>
					</div>
					<div>
						<label className="text-sm text-slate-400">Student</label>
						<select
							value={studentId}
							onChange={(e) => setStudentId(e.target.value)}
							disabled={!sectionId}
							className={inputClass}
						>
							<option value="">Select student</option>
							{roster.map((s) => (
								<option key={s.id} value={s.id}>
									{s.full_name}
								</option>
							))}
						</select>
					</div>
					<div>
						<label className="text-sm text-slate-400">Marks obtained</label>
						<input
							type="number"
							value={marks}
							onChange={(e) => setMarks(e.target.value)}
							className={inputClass}
							placeholder="78"
						/>
					</div>
					<div>
						<label className="text-sm text-slate-400">Max marks</label>
						<input
							type="number"
							value={maxMarks}
							onChange={(e) => setMaxMarks(e.target.value)}
							className={inputClass}
						/>
					</div>
				</div>

				{error && (
					<p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
						{error}
					</p>
				)}
				{success && (
					<p className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
						{success}
					</p>
				)}

				<button
					onClick={save}
					disabled={saving}
					className="mt-4 rounded-lg bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
				>
					{saving ? "Saving..." : "Save marks"}
				</button>
			</div>

			{/* Results for the selected subject */}
			{subjectId && (
				<div className="mt-8">
					<h3 className="text-lg font-semibold">Recorded results</h3>
					{results.length === 0 ? (
						<p className="mt-3 text-slate-400">
							No marks recorded for this subject yet.
						</p>
					) : (
						<div className="mt-3 space-y-2">
							{results.map((r) => {
								const pct = Math.round(
									(r.marks_obtained / r.max_marks) * 100,
								)
								return (
									<div
										key={r.id}
										className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3"
									>
										<span className="text-sm text-slate-200">
											{nameFor(r.student_id)}
										</span>
										<span className="text-sm text-slate-400">
											{r.marks_obtained}/{r.max_marks} ({pct}%) -{" "}
											<span className={gradeColor(r.grade_point)}>
												GP {r.grade_point}
											</span>
										</span>
									</div>
								)
							})}
						</div>
					)}
				</div>
			)}
		</div>
	)
}
