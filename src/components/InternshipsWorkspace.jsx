import React, { useEffect, useRef, useState } from 'react'
import { ArrowLeft, PencilLine, Plus, RotateCcw } from 'lucide-react'
import { loadCanonicalQuestionsRequest } from '../api/canonicalQuestions'
import { loadInternshipRequest, loadInternshipsRequest } from '../api/internships'
import { InternshipDetail } from './internships/InternshipDetail'
import { useUnsavedGuard } from '../hooks/useUnsavedGuard'
import './knowledge.css'
import './internships.css'

export function InternshipsWorkspace({ selectedId, mode = 'view', navigate = () => {} }) {
  const [internships, setInternships] = useState([])
  const [selected, setSelected] = useState(null)
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dirty, setDirty] = useState(false)
  const requestVersion = useRef(0)
  const selectedIdRef = useRef(selectedId)
  selectedIdRef.current = selectedId
  useUnsavedGuard(dirty && mode === 'edit', '实习资产包还有未保存的修改，确定离开吗？')
  function replaceInternship(item) {
    setInternships((current) => {
      const exists = current.some((candidate) => candidate.id === item.id)
      return exists ? current.map((candidate) => candidate.id === item.id ? item : candidate) : [item, ...current]
    })
    if (selectedIdRef.current === item.id) {
      setSelected(item)
      setDirty(false)
    }
    setError('')
  }

  async function refresh() {
    const version = ++requestVersion.current
    setLoading(true)
    if (selectedId) setSelected(null)
    try {
      if (selectedId) {
        const item = await loadInternshipRequest(selectedId)
        if (version !== requestVersion.current) return
        setSelected(item)
        setError('')
        return
      }
      const items = await loadInternshipsRequest()
      if (version !== requestVersion.current) return
      setInternships(items)
      setSelected(null)
      setError('')
    } catch (caught) { if (version === requestVersion.current) setError(caught.message) } finally { if (version === requestVersion.current) setLoading(false) }
  }

  useEffect(() => {
    refresh()
    if (selectedId) loadCanonicalQuestionsRequest({ limit: 100 }).then(setQuestions).catch(() => setQuestions([]))
  }, [selectedId])
  useEffect(() => { setDirty(false) }, [selectedId, mode])

  return <section className={`internships-workspace ${selectedId ? 'internship-detail-page' : 'internship-index-page'} ${mode === 'edit' ? 'track-edit-mode' : 'track-view-mode'}`} onChangeCapture={() => selectedId && mode === 'edit' && setDirty(true)}>
    {selectedId && <><button className="track-back" type="button" onClick={() => navigate('/internships')}><ArrowLeft size={17} />返回实习轨道</button><nav className="track-breadcrumb" aria-label="面包屑"><button onClick={() => navigate('/internships')}>实习</button><span>/</span><b>{selected ? `${selected.organization} · ${selected.role_title}` : '实习详情'}</b></nav></>}
    <header className="internships-heading">
      <div><p className="track-eyebrow">准备轨道 · 实习</p><h2>{selectedId ? selected ? `${selected.organization} · ${selected.role_title}` : '实习详情' : '把职责边界讲得具体可信'}</h2><p>{selectedId ? '基本事实、STAR、材料和情报信号保持清晰边界。' : '事实、表达和面经信号分开维护；先核实，再组织 STAR 与量化表达。'}</p></div>
      <div className="track-heading-actions">{selectedId && <button className="refresh-action" onClick={() => navigate(mode === 'edit' ? `/internships/${selectedId}` : `/internships/${selectedId}/edit`)}><PencilLine size={15} />{mode === 'edit' ? '结束编辑' : '编辑资产包'}</button>}<button className="refresh-action" onClick={refresh}><RotateCcw size={15} />刷新</button></div>
    </header>
    {error && <p className="internships-error">{error}</p>}
    {!selectedId ? <div className="internships-index-layout">
      <aside className="internships-rail">
        <button className="track-new-page-link" onClick={() => navigate('/internships/new')}><Plus size={16} /><span><strong>新建实习资产包</strong><small>进入独立页面整理基本事实</small></span></button>
        <div className="internship-list">
          {internships.map((item) => <button key={item.id} onClick={() => navigate(`/internships/${item.id}`)}>
            <strong>{item.organization}</strong><span>{item.role_title} · 事实 {item.facts.length} · 材料 {item.materials.length}</span><small>{item.status === 'active' ? '持续维护' : '已归档'} · 更新于 {new Date(item.updated_at).toLocaleDateString('zh-CN')}</small>
          </button>)}
          {loading && <p>正在读取实习资产…</p>}{!loading && internships.length === 0 && <p>还没有实习资产，从一段可核实的职责或结果开始。</p>}
        </div>
      </aside>
      <section className="internships-index-intro"><span className="track-section-label">边界优先</span><h3>先说明“我负责什么”</h3><p>职责与团队边界是 STAR 的地基。量化结果必须来自已核实事实，面经信号只能解释岗位关注点，不能改写经历。</p><dl><div><dt>经历</dt><dd>{internships.length}</dd></div><div><dt>事实</dt><dd>{internships.reduce((sum, item) => sum + item.facts.length, 0)}</dd></div><div><dt>可用材料</dt><dd>{internships.reduce((sum, item) => sum + item.materials.filter((material) => ['ready', 'verified'].includes(material.preparation_status)).length, 0)}</dd></div></dl></section>
    </div> : !selected ? <div className="internship-empty">{loading ? '正在读取实习资产包…' : error || '实习经历不存在'}</div> : <InternshipDetail
        key={selected.id}
        internship={selected}
        questions={questions}
        onChange={replaceInternship}
        onError={setError}
        onRefresh={refresh}
      />}
  </section>
}
