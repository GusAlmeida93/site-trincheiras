import type { components } from './types.gen';

export type LessonBundle = components['schemas']['LessonBundle'];
export type LessonRead = components['schemas']['LessonRead'];
// Activities as the public bundle ships them: no answers, no scoring rules.
export type PublicActivity = components['schemas']['PublicActivity'];
export type PublicQuestion = components['schemas']['PublicQuestion'];
export type PublicQuestionOption = components['schemas']['PublicQuestionOption'];
export type PublicMatchDocument = components['schemas']['PublicMatchDocument'];
export type MapRegionRead = components['schemas']['MapRegionRead'];
export type MapFeatureRead = components['schemas']['MapFeatureRead'];
export type PlayerCreate = components['schemas']['PlayerCreate'];
export type PlayerRead = components['schemas']['PlayerRead'];
export type AnswerCreate = components['schemas']['AnswerCreate'];
export type AnswerResult = components['schemas']['AnswerResult'];
