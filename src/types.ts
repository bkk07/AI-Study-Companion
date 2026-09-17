export type MasteryLevel = 'mastered' | 'developing' | 'weak' | 'unassessed';
export type ConfidenceLevel = 'low' | 'medium' | 'high';

export type View =
  | 'login' | 'register'
  | 'spaces' | 'projects'
  | 'overview' | 'documents' | 'structure' | 'tutor'
  | 'flashcards' | 'quiz' | 'assessments'
  | 'dashboard' | 'analytics' | 'activity' | 'settings'
  | 'admin';

export interface Space {
  id: string;
  name: string;
  description: string;
  projectCount: number;
  lastActivity: string;
  color: string;
}

export interface Project {
  id: string;
  spaceId: string;
  name: string;
  description: string;
  documentCount: number;
  topicCount: number;
  conceptCount: number;
  mcqMastery: number | null;
  appliedMastery: number | null;
  lastActivity: string;
}

export interface Concept {
  id: string;
  name: string;
  description: string;
  topicId: string;
  subtopicId: string;
  mastery: MasteryLevel;
  mcqMastery: number | null;
  appliedMastery: number | null;
  confidence: ConfidenceLevel | null;
  quizAttempts: number;
  appliedAssessments: number;
  flashcardReviews: number;
  source: { document: string; page: number };
  lastPracticed: string | null;
}

export interface Topic {
  id: string;
  name: string;
  subtopics: Subtopic[];
}

export interface Subtopic {
  id: string;
  name: string;
  topicId: string;
  concepts: Concept[];
}

export interface Document {
  id: string;
  name: string;
  pages: number;
  chunks: number;
  size: string;
  status: 'queued' | 'processing' | 'ready' | 'failed';
  uploadedAt: string;
  topicsDetected: number;
  subtopicsDetected: number;
  conceptsDetected: number;
}

export interface Flashcard {
  id: string;
  front: string;
  back: string;
  concept: string;
  source: string;
  state: 'new' | 'learning' | 'mastered';
  lastReviewed: string | null;
  nextReview: string | null;
}

export interface QuizQuestion {
  id: string;
  stem: string;
  options: string[];
  correctIndex: number;
  conceptId: string;
  conceptName: string;
  reason: string;
}

export interface AppState {
  isAuthenticated: boolean;
  view: View;
  selectedSpaceId: string | null;
  selectedProjectId: string | null;
  sidebarCollapsed: boolean;
  commandOpen: boolean;
}
