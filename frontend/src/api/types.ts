import type { components } from './types.gen';

export type LessonBundle = components['schemas']['LessonBundle'];
export type LessonRead = components['schemas']['LessonRead'];
export type ActivityRead = components['schemas']['ActivityRead'];
export type QuestionRead = components['schemas']['QuestionRead'];
export type QuestionOptionRead = components['schemas']['QuestionOptionRead'];
export type MatchDocumentRead = components['schemas']['MatchDocumentRead'];
export type MapRegionRead = components['schemas']['MapRegionRead'];
export type MapFeatureRead = components['schemas']['MapFeatureRead'];
export type PlayerCreate = components['schemas']['PlayerCreate'];
export type PlayerRead = components['schemas']['PlayerRead'];
export type AnswerCreate = components['schemas']['AnswerCreate'];
export type AnswerRead = components['schemas']['AnswerRead'];

export interface ScoringConfig {
  pointsCorrect: number;
  pointsWrong: number;
  maxPenalizedErrors: number;
}

/** Activity config is free-form JSON in the API; narrow it with defaults. */
export function readScoringConfig(config: ActivityRead['config']): ScoringConfig {
  const raw = (config ?? {}) as Record<string, unknown>;
  const num = (value: unknown, fallback: number): number =>
    typeof value === 'number' && Number.isFinite(value) ? value : fallback;
  return {
    pointsCorrect: num(raw['points_correct'], 10),
    pointsWrong: num(raw['points_wrong'], -5),
    maxPenalizedErrors: num(raw['max_penalized_errors'], 2),
  };
}
