import type { components } from '@schorder/contract'

/**
 * 直接取自 OpenAPI 生成的类型，前端不手写接口结构。
 *
 * 注意：这里用的是 **MetaOut**（信封里的 data 部分），不是 MetaEnvelope。
 * `apiRequest` 已经拆过一层信封，泛型参数要填 data 的类型。
 */
export type MetaData = components['schemas']['MetaOut']