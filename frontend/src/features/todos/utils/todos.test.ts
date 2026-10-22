import { env } from 'node:process'
import { describe, expect, it, vi } from 'vitest'
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

  it('shows only unfinished tasks due before the current local calendar day', () => {
    const previousTimeZone = env.TZ
    env.TZ = 'America/Los_Angeles'
    vi.useFakeTimers()

    try {
      // 22:30 on October 2 locally, but October 3 in UTC.
      vi.setSystemTime(new Date('2026-10-03T05:30:00Z'))
      const todos: Todo[] = [
        { ...base, id: 1, due_date: '2026-10-01' },
        { ...base, id: 2, due_date: '2026-10-02' },
        { ...base, id: 3, due_date: '2026-10-03' },
        { ...base, id: 4, due_date: null },
        { ...base, id: 5, due_date: '2026-10-01', completed: true },
      ]

      expect(selectTodos(todos, 'overdue', '', 'newest')).toEqual([todos[0]])
    } finally {
      vi.useRealTimers()
      if (previousTimeZone === undefined) delete env.TZ
      else env.TZ = previousTimeZone
    }
  })

  it('sorts by priority without changing the source array', () => {
    const high: Todo = { ...base, id: 2, priority: 'high' }
    const todos = [base, high]
    expect(selectTodos(todos, 'all', '', 'priority')).toEqual([high, base])
    expect(todos).toEqual([base, high])
  })
})
