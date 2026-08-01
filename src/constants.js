export const STAGES = [
  { key: 'saved', label: '待评估', short: '评估', index: '01', tone: 'graphite' },
  { key: 'applied', label: '已投递', short: '投递', index: '02', tone: 'cobalt' },
  { key: 'interview', label: '面试中', short: '面试', index: '03', tone: 'coral' },
  { key: 'offer', label: 'Offer', short: 'Offer', index: '04', tone: 'acid' },
  { key: 'closed', label: '已结束', short: '归档', index: '05', tone: 'ash' },
]

export const EMPTY_APPLICATION = {
  company: '',
  role: '',
  stage: 'saved',
  key_date: '',
  next_action: '',
  channel: '',
  notes: '',
  url: '',
}

export const EMPTY_PROFILE = { title: '', location: '', focus: '', summary: '' }
