import { afterEach, describe, expect, it, vi } from 'vitest'
import { selectTodos } from './todos'
import type { Todo } from '../types'

const base: Todo = {
  id: 1,
  title: 'Sprint plan',
  description: '',
  priority: 'medium',
  completed: false,
  due_date: null,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
}

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllEnvs()
})

describe('selectTodos', () => {
  it('combines status with a case-insensitive search in the description', () => {
    const matching = { ...base, description: 'Discuss the API' }
    const todos = [
      matching,
      { ...matching, id: 2, completed: true },
      { ...base, id: 3 },
    ]
    expect(selectTodos(todos, 'active', ' api ', 'newest')).toEqual([matching])
  })

  it('sorts by priority without changing the source array', () => {
    const high: Todo = { ...base, id: 2, priority: 'high' }
    const todos = [base, high]
    expect(selectTodos(todos, 'all', '', 'priority')).toEqual([high, base])
    expect(todos).toEqual([base, high])
  })

  it('shows only unfinished tasks due before the local calendar day as overdue', () => {
    vi.stubEnv('TZ', 'America/Los_Angeles')
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-10T06:30:00.000Z'))

    expect(new Date().getDate()).toBe(9)

    const overdue: Todo = { ...base, id: 1, due_date: '2026-06-08' }
    const todos = [
      overdue,
      { ...base, id: 2, completed: true, due_date: '2026-06-08' },
      { ...base, id: 3, due_date: '2026-06-09' },
      { ...base, id: 4, due_date: '2026-06-10' },
      { ...base, id: 5, due_date: null },
    ]

    expect(selectTodos(todos, 'overdue', '', 'newest')).toEqual([overdue])
  })
})
