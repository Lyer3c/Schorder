/**
 * 契约入口。
 *
 * types.ts 由 `npm run gen:contract` 从 FastAPI 生成的 openapi.json 产出，
 * 禁止手改；改接口请改后端 Pydantic 模型后重新生成。
 */
export type { components, operations, paths } from './types'