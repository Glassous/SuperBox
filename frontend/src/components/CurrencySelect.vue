<script setup lang="ts">
import { computed, ref } from 'vue'
import { currencyName } from '../data/currencyNames'
const props = defineProps<{ label: string; modelValue: string; items: { code: string; name: string }[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const query = ref(''), container = ref<HTMLDetailsElement>()
const filtered = computed(() => props.items.filter(item =>
  `${item.code} ${item.name} ${currencyName(item.code, item.name)}`.toLowerCase().includes(query.value.trim().toLowerCase())))
const selected = computed(() => props.items.find(item => item.code === props.modelValue))
function choose(value: string) {
  emit('update:modelValue', value)
  if (container.value) container.value.open = false
  query.value = ''
}
</script>
<template>
  <details ref="container" class="rounded-xl border border-slate-200 p-3 dark:border-white/10">
    <summary class="cursor-pointer text-sm"><span class="text-slate-500">{{ label }}</span> <strong class="ml-2">{{ modelValue }}</strong><span v-if="selected" class="ml-2">{{ currencyName(selected.code, selected.name) }}</span></summary>
    <label class="mt-3 block text-xs text-slate-500">搜索{{ label }}<input v-model="query" class="tool-input" placeholder="输入代码或名称" /></label>
    <select :value="modelValue" :aria-label="label" size="6" class="tool-input" :disabled="!items.length" @change="choose(($event.target as HTMLSelectElement).value)">
      <option v-for="item in filtered" :key="item.code" :value="item.code">{{ item.code }} · {{ currencyName(item.code, item.name) }}</option>
    </select>
    <p v-if="!filtered.length" class="mt-2 text-xs text-slate-500">没有匹配的货币</p>
  </details>
</template>
