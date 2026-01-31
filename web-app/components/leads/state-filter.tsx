'use client'

import { useState, useRef, useEffect } from 'react'
import { Check, ChevronDown, X } from 'lucide-react'
import { US_STATES } from '@/lib/constants/us-states'
import { cn } from '@/lib/utils/cn'

interface StateFilterProps {
  selected: string[]
  onChange: (states: string[]) => void
  className?: string
}

export function StateFilter({ selected, onChange, className }: StateFilterProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const toggleState = (code: string) => {
    if (selected.includes(code)) {
      onChange(selected.filter(s => s !== code))
    } else {
      onChange([...selected, code])
    }
  }

  const selectAll = () => {
    onChange(US_STATES.map(s => s.code))
  }

  const clearAll = () => {
    onChange([])
  }

  const filteredStates = US_STATES.filter(
    state =>
      state.name.toLowerCase().includes(search.toLowerCase()) ||
      state.code.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div ref={dropdownRef} className={cn('relative', className)}>
      {/* Trigger Button */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 bg-white dark:bg-gray-800 min-w-[140px] transition-colors"
      >
        <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
          {selected.length === 0
            ? 'All States'
            : selected.length === 1
            ? US_STATES.find(s => s.code === selected[0])?.name
            : `${selected.length} States`}
        </span>
        <div className="flex items-center gap-2">
          {selected.length > 0 && (
            <span className="flex items-center justify-center h-5 min-w-[20px] px-1.5 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 rounded-full text-xs font-semibold">
              {selected.length}
            </span>
          )}
          <ChevronDown
            className={cn(
              'h-4 w-4 text-gray-500 transition-transform',
              open && 'transform rotate-180'
            )}
          />
        </div>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute top-full mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
          {/* Header with actions */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                Filter by State
              </span>
              <button
                onClick={() => setOpen(false)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              >
                <X className="h-4 w-4 text-gray-500" />
              </button>
            </div>

            {/* Search */}
            <input
              type="text"
              placeholder="Search states..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              autoFocus
            />
          </div>

          {/* Quick Actions */}
          <div className="p-2 border-b border-gray-200 dark:border-gray-700 flex justify-between">
            <button
              onClick={selectAll}
              className="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium"
            >
              Select All
            </button>
            <button
              onClick={clearAll}
              className="text-xs text-gray-600 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 font-medium"
            >
              Clear
            </button>
          </div>

          {/* States List */}
          <div className="max-h-64 overflow-y-auto custom-scrollbar">
            {filteredStates.length === 0 ? (
              <div className="p-4 text-center text-sm text-gray-500">
                No states found
              </div>
            ) : (
              <div className="p-2">
                {filteredStates.map(state => {
                  const isSelected = selected.includes(state.code)
                  return (
                    <button
                      key={state.code}
                      onClick={() => toggleState(state.code)}
                      className={cn(
                        'flex items-center justify-between w-full px-3 py-2 text-sm rounded-md transition-colors',
                        isSelected
                          ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                          : 'hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200'
                      )}
                    >
                      <span className="flex items-center gap-2">
                        <span className="w-8 text-xs font-mono text-gray-500 dark:text-gray-400">
                          {state.code}
                        </span>
                        <span>{state.name}</span>
                      </span>
                      {isSelected && (
                        <Check className="h-4 w-4 text-primary-600 dark:text-primary-400" />
                      )}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          {selected.length > 0 && (
            <div className="p-3 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400 text-center">
              {selected.length} state{selected.length !== 1 ? 's' : ''} selected
            </div>
          )}
        </div>
      )}
    </div>
  )
}
