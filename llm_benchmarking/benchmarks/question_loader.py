#!/usr/bin/env python3
"""
Question Loader
Loads questions from generated_questions.json for benchmarking
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Question:
    """Represents a benchmark question with expected answers."""
    id: str
    question: str
    category: str
    sql_formula: str
    excel_formula: str
    calculation_steps: List[str]
    answer_format: str
    related_tables: List[str]
    related_columns: List[str]
    correct_answer: str


class QuestionLoader:
    """Loads and manages benchmark questions."""
    
    def __init__(self, questions_file: Optional[Path] = None):
        if questions_file is None:
            # Default path relative to project root
            questions_file = Path(__file__).parent.parent.parent / "question_generator" / "generated_questions.json"
        
        self.questions_file = Path(questions_file)
        self.questions: Dict[str, List[Question]] = {}
        self.all_questions: List[Question] = []
        self.metadata: Dict = {}
        
        self._load_questions()
    
    def _load_questions(self):
        """Load questions from JSON file."""
        if not self.questions_file.exists():
            raise FileNotFoundError(f"Questions file not found: {self.questions_file}")
        
        with open(self.questions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.metadata = data.get('metadata', {})
        questions_data = data.get('questions', {})
        
        for category, category_questions in questions_data.items():
            self.questions[category] = []
            for q in category_questions:
                question = Question(
                    id=q.get('id', ''),
                    question=q.get('question', ''),
                    category=q.get('category', category),
                    sql_formula=q.get('sql_formula', ''),
                    excel_formula=q.get('excel_formula', ''),
                    calculation_steps=q.get('calculation_steps', []),
                    answer_format=q.get('answer_format', ''),
                    related_tables=q.get('related_tables', []),
                    related_columns=q.get('related_columns', []),
                    correct_answer=q.get('correct_answer', '')
                )
                self.questions[category].append(question)
                self.all_questions.append(question)
        
        print(f"Loaded {len(self.all_questions)} questions from {self.questions_file.name}")
        for cat, qs in self.questions.items():
            print(f"  - {cat}: {len(qs)} questions")
    
    def get_all(self) -> List[Question]:
        """Get all questions."""
        return self.all_questions
    
    def get_by_category(self, category: str) -> List[Question]:
        """Get questions by category."""
        return self.questions.get(category, [])
    
    def get_by_id(self, question_id: str) -> Optional[Question]:
        """Get a specific question by ID."""
        for q in self.all_questions:
            if q.id == question_id:
                return q
        return None
    
    def sample(self, n: int, category: Optional[str] = None, 
               seed: Optional[int] = None) -> List[Question]:
        """
        Sample n questions randomly.
        
        Args:
            n: Number of questions to sample
            category: Optional category to sample from
            seed: Random seed for reproducibility
        
        Returns:
            List of sampled questions
        """
        if seed is not None:
            random.seed(seed)
        
        if category:
            pool = self.get_by_category(category)
        else:
            pool = self.all_questions
        
        n = min(n, len(pool))
        return random.sample(pool, n)
    
    def sample_balanced(self, n_per_category: int, 
                        seed: Optional[int] = None) -> List[Question]:
        """
        Sample equal number of questions from each category.
        
        Args:
            n_per_category: Number of questions per category
            seed: Random seed for reproducibility
        
        Returns:
            List of sampled questions
        """
        if seed is not None:
            random.seed(seed)
        
        sampled = []
        for category, questions in self.questions.items():
            n = min(n_per_category, len(questions))
            sampled.extend(random.sample(questions, n))
        
        return sampled
    
    def get_categories(self) -> List[str]:
        """Get list of available categories."""
        return list(self.questions.keys())
    
    def get_stats(self) -> Dict:
        """Get statistics about loaded questions."""
        return {
            'total_questions': len(self.all_questions),
            'categories': {cat: len(qs) for cat, qs in self.questions.items()},
            'metadata': self.metadata
        }
    
    def to_benchmark_format(self, questions: List[Question]) -> List[Dict]:
        """Convert questions to benchmark-ready format."""
        return [
            {
                'id': q.id,
                'question': q.question,
                'category': q.category,
                'expected': {
                    'sql_formula': q.sql_formula,
                    'calculation_steps': q.calculation_steps,
                    'related_tables': q.related_tables,
                    'related_columns': q.related_columns,
                    'correct_answer': q.correct_answer
                }
            }
            for q in questions
        ]
