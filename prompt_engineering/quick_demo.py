#!/usr/bin/env python3
"""
Quick Demo of Enhanced Prompt Engineering
Shows how enhanced prompts work for Llama 4 Maverick
"""

from llama4_maverick_optimizer import EnhancedPromptEngineer

def main():
    print("="*70)
    print("Enhanced Prompt Engineering - Quick Demo")
    print("="*70)
    
    # Initialize optimizer
    optimizer = EnhancedPromptEngineer()
    
    # Example questions
    test_questions = [
        {
            "id": "demo_1",
            "question": "What is the total number of components reworked in Line-2?",
            "category": "Easy"
        },
        {
            "id": "demo_2",
            "question": "What is the correlation between downtime minutes and failed quantity per line machine and product?",
            "category": "Complex"
        }
    ]
    
    for question in test_questions:
        print(f"\n{'='*70}")
        print(f"Question: {question['question']}")
        print(f"Category: {question['category']}")
        print(f"{'='*70}\n")
        
        # Generate enhanced methodology prompt
        print("📝 Enhanced Methodology Prompt:")
        print("-" * 70)
        methodology_prompt = optimizer.generate_enhanced_methodology_prompt(
            question['question'],
            question['category']
        )
        print(methodology_prompt[:500] + "...\n")
        
        # Generate enhanced SQL prompt
        print("📝 Enhanced SQL Prompt:")
        print("-" * 70)
        sql_prompt = optimizer.generate_enhanced_sql_prompt(question['question'])
        print(sql_prompt[:500] + "...\n")
        
        # Show question type identification
        question_type = optimizer._identify_question_type(question['question'])
        print(f"🔍 Identified Question Type: {question_type}")
        print(f"📚 Using Few-Shot Example: {question_type}\n")
    
    print("\n" + "="*70)
    print("Demo Complete!")
    print("="*70)
    print("\nTo test with actual LLM queries, run:")
    print("  python3 llama4_maverick_optimizer.py")
    print("\nTo run full evaluation, run:")
    print("  python3 test_enhanced_prompts.py")


if __name__ == "__main__":
    main()


