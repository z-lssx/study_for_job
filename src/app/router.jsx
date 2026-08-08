import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

function currentLocation() {
  return { pathname: window.location.pathname, search: window.location.search }
}

export function useAppRouter() {
  const [location, setLocation] = useState(currentLocation)
  const locationRef = useRef(location)

  useEffect(() => {
    const handlePopState = () => {
      const next = currentLocation()
      const navigationEvent = new CustomEvent('app:navigate', { cancelable: true, detail: { to: `${next.pathname}${next.search}` } })
      if (!window.dispatchEvent(navigationEvent)) {
        const current = locationRef.current
        window.history.pushState({}, '', `${current.pathname}${current.search}`)
        return
      }
      locationRef.current = next
      setLocation(next)
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const navigate = useCallback((to, options = {}) => {
    const navigationEvent = new CustomEvent('app:navigate', { cancelable: true, detail: { to } })
    if (!window.dispatchEvent(navigationEvent)) return false
    const next = new URL(to, window.location.origin)
    window.history[options.replace ? 'replaceState' : 'pushState']({}, '', `${next.pathname}${next.search}`)
    const nextLocation = currentLocation()
    locationRef.current = nextLocation
    setLocation(nextLocation)
    if (!options.preserveScroll) {
      const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' })
    }
    return true
  }, [])

  return useMemo(() => ({ ...location, navigate }), [location, navigate])
}

export function AppLink({ to, navigate, children, ...props }) {
  return <a
    href={to}
    onClick={(event) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
      event.preventDefault()
      navigate(to)
    }}
    {...props}
  >{children}</a>
}

export function routeFromPath(pathname) {
  const segments = pathname.split('/').filter(Boolean).map((segment) => {
    try { return decodeURIComponent(segment) } catch { return segment }
  })
  if (segments.length === 0) return { name: 'today', section: 'today' }
  if (segments[0] === 'profile') return { name: 'profile', section: 'profile' }
  if (segments[0] === 'applications') return { name: 'applications', section: 'applications', id: segments[1] || null }
  if (segments[0] === 'planning') return { name: 'planning', section: 'planning' }
  if (segments[0] === 'intelligence') {
    if (segments[1] === 'search') return { name: 'intelligence-search', section: 'intelligence' }
    if (segments[1] === 'questions') return { name: 'intelligence-questions', section: 'intelligence', id: segments[2] || null }
    return { name: segments[1] ? 'intelligence-detail' : 'intelligence', section: 'intelligence', id: segments[1] || null }
  }
  if (segments[0] === 'knowledge') return { name: segments[1] ? 'knowledge-detail' : 'knowledge', section: 'knowledge', id: segments[1] || null }
  if (segments[0] === 'algorithms') return { name: segments[1] ? 'algorithm-detail' : 'algorithms', section: 'algorithms', id: segments[1] || null }
  if (segments[0] === 'projects') {
    if (segments[1] === 'new') return { name: 'project-new', section: 'projects' }
    if (segments[1] && segments[2] === 'edit') return { name: 'project-edit', section: 'projects', id: segments[1], mode: 'edit' }
    return { name: segments[1] ? 'project-detail' : 'projects', section: 'projects', id: segments[1] || null, mode: 'view' }
  }
  if (segments[0] === 'internships') {
    if (segments[1] === 'new') return { name: 'internship-new', section: 'internships' }
    if (segments[1] && segments[2] === 'edit') return { name: 'internship-edit', section: 'internships', id: segments[1], mode: 'edit' }
    return { name: segments[1] ? 'internship-detail' : 'internships', section: 'internships', id: segments[1] || null, mode: 'view' }
  }
  if (segments[0] === 'exports') return { name: 'exports', section: 'exports' }
  if (segments[0] === 'settings' && segments[1] === 'ai') return { name: 'ai', section: 'ai' }
  return { name: 'not-found', section: '' }
}
