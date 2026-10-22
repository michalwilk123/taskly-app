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

  it('filters overdue tasks due before today, excluding completed and non-overdue tasks', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-15T12:00:00.000Z'))
    try {
      const overdue = { ...base, id: 1, due_date: '2026-10-14' }
      const todos = [
        overdue,
        { ...base, id: 2, completed: true, due_date: '2026-10-14' },
        { ...base, id: 3, due_date: '2026-10-15' },
        { ...base, id: 4, due_date: '2026-10-16' },
        { ...base, id: 5, due_date: null },
      ]

      expect(selectTodos(todos, 'overdue', '', 'newest')).toEqual([overdue])
    } finally {
      vi.useRealTimers()
    }
  })

  it('sorts by priority without changing the source array', () => {
    const high: Todo = { ...base, id: 2, priority: 'high' }
    const todos = [base, high]
    expect(selectTodos(todos, 'all', '', 'priority')).toEqual([high, base])
    expect(todos).toEqual([base, high])
  })
})
