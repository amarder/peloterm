import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCounterStore } from '../counter'

describe('Counter Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should initialize with count of 0', () => {
    const store = useCounterStore()
    expect(store.count).toBe(0)
  })

  it('should calculate doubleCount correctly', () => {
    const store = useCounterStore()
    
    expect(store.doubleCount).toBe(0)
    
    store.count = 5
    expect(store.doubleCount).toBe(10)
    
    store.count = -3
    expect(store.doubleCount).toBe(-6)
  })

  it('should increment count when increment is called', () => {
    const store = useCounterStore()
    
    expect(store.count).toBe(0)
    
    store.increment()
    expect(store.count).toBe(1)
    
    store.increment()
    expect(store.count).toBe(2)
  })

  it('should update doubleCount when count is incremented', () => {
    const store = useCounterStore()
    
    expect(store.doubleCount).toBe(0)
    
    store.increment()
    expect(store.doubleCount).toBe(2)
    
    store.increment()
    expect(store.doubleCount).toBe(4)
  })

  it('should allow direct count modification', () => {
    const store = useCounterStore()
    
    store.count = 42
    expect(store.count).toBe(42)
    expect(store.doubleCount).toBe(84)
  })

  it('should maintain reactivity across multiple store instances', () => {
    const store1 = useCounterStore()
    const store2 = useCounterStore()
    
    // Should be the same instance
    expect(store1).toBe(store2)
    
    store1.increment()
    expect(store2.count).toBe(1)
    expect(store2.doubleCount).toBe(2)
  })
}) 