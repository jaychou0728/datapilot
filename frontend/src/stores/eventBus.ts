import mitt from 'mitt'

type Events = {
  'dataset:cleaned': void
  'dataset:undo': void
  'dataset:rollback': void
  'agent:done': { report_id: string }
  'chart:refresh': void
  'preview:refresh': void
}

export const bus = mitt<Events>()
