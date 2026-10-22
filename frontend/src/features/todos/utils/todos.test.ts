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

  it('sorts by priority without changing the source array', () => {
    const high: Todo = { ...base, id: 2, priority: 'high' }
    const todos = [base, high]
    expect(selectTodos(todos, 'all', '', 'priority')).toEqual([high, base])
    expect(todos).toEqual([base, high])
  })

  it('filters unfinished tasks overdue by the local calendar day', () => {
    vi.stubEnv('TZ', 'Pacific/Auckland')
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-14T12:30:00.000Z'))

    try {
      const overdue: Todo = { ...base, id: 1, due_date: '2026-06-14' }
      const dueToday: Todo = { ...base, id: 2, due_date: '2026-06-15' }
      const dueLater: Todo = { ...base, id: 3, due_date: '2026-06-16' }
      const completedOverdue: Todo = {
        ...base,
        id: 4,
        due_date: '2026-06-14',
        completed: true,
      }
      const noDueDate: Todo = { ...base, id: 5 }

      expect(
        selectTodos(
          [overdue, dueToday, dueLater, completedOverdue, noDueDate],
          'overdue',
          '',
          'newest',
        ),
      ).toEqual([overdue])
    } finally {
      vi.useRealTimers()
      vi.unstubAllEnvs()
    }
  })
})
