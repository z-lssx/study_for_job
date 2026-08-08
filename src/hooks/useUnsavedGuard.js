import { useEffect } from 'react'

export function useUnsavedGuard(dirty, message = '还有未保存的修改，确定离开吗？') {
  useEffect(() => {
    if (!dirty) return undefined
    const warnBeforeLeave = (event) => { event.preventDefault(); event.returnValue = '' }
    const confirmNavigation = (event) => {
      if (!window.confirm(message)) event.preventDefault()
    }
    window.addEventListener('beforeunload', warnBeforeLeave)
    window.addEventListener('app:navigate', confirmNavigation)
    return () => {
      window.removeEventListener('beforeunload', warnBeforeLeave)
      window.removeEventListener('app:navigate', confirmNavigation)
    }
  }, [dirty, message])
}
