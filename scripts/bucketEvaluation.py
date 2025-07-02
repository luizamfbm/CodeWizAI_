import json
import logging
from typing import List, Dict, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class BucketValidator:
    """
    Class to validate and test the quality of bucket classification
    """
    
    def __init__(self):
        # Test examples based on meeting context
        self.test_cases = [
            {
                "text": "When a new lead comes in through a phone call, the system automatically captures their information and assigns them to a franchisee based on location.",
                "expected_bucket": "lead_sources",
                "user_type": "franchisee",
                "description": "Lead entry via phone call"
            },
            {
                "text": "After the trial class, we need to follow up with the lead within 24 hours to schedule their consultation and discuss enrollment options.",
                "expected_bucket": "sales_process",
                "user_type": "franchisee",
                "description": "Post-trial class follow-up"
            },
            {
                "text": "The Zoho workflow automatically sends a reminder email to staff when a lead status changes to 'scheduled' for their trial class.",
                "expected_bucket": "crm_workflows",
                "user_type": "staff",
                "description": "CRM automation workflow"
            },
            {
                "text": "What happens when a lead doesn't show up for their trial class? The system should mark them as 'no show' and trigger a follow-up sequence.",
                "expected_bucket": "sales_process",
                "user_type": "franchisee",
                "description": "No-show handling process"
            },
            {
                "text": "Book me integration allows leads to self-schedule their trial classes directly through the website form.",
                "expected_bucket": "lead_sources",
                "user_type": "staff",
                "description": "Self-scheduling integration"
            },
            {
                "text": "The conversion rate report shows how many leads convert from trial class to paid enrollment by franchisee location.",
                "expected_bucket": "reporting",
                "user_type": "leadership",
                "description": "Conversion analytics"
            },
            {
                "text": "When creating a lead manually, staff members need to ensure all required fields are populated including lead source and assigned franchisee.",
                "expected_bucket": "lead_sources",
                "user_type": "staff",
                "description": "Manual lead creation"
            },
            {
                "text": "Technical support ticket: Integration with iClass Pro is not syncing student enrollment data properly.",
                "expected_bucket": "technical_support",
                "user_type": "staff",
                "description": "Technical integration issue"
            }
        ]
    
    def run_validation_tests(self, classifier) -> Dict:
        """
        Runs classification validation tests
        """
        results = {
            "total_tests": len(self.test_cases),
            "passed": 0,
            "failed": 0,
            "test_results": [],
            "accuracy": 0.0
        }
        
        logging.info("🧪 Running bucket classification validation tests...")
        
        for i, test_case in enumerate(self.test_cases):
            predicted_bucket = classifier.get_primary_bucket(
                test_case["text"], 
                test_case["user_type"]
            )
            
            is_correct = predicted_bucket == test_case["expected_bucket"]
            
            if is_correct:
                results["passed"] += 1
                status = "✅ PASS"
            else:
                results["failed"] += 1
                status = "❌ FAIL"
            
            # Get detailed scores
            scores = classifier.classify_chunk(test_case["text"], test_case["user_type"])
            
            test_result = {
                "test_id": i + 1,
                "description": test_case["description"],
                "expected": test_case["expected_bucket"],
                "predicted": predicted_bucket,
                "correct": is_correct,
                "confidence": scores.get(predicted_bucket, 0.0),
                "all_scores": scores,
                "user_type": test_case["user_type"]
            }
            
            results["test_results"].append(test_result)
            
            logging.info(f"{status} Test {i+1}: {test_case['description']}")
            logging.info(f"   Expected: {test_case['expected_bucket']}, Got: {predicted_bucket}")
            if not is_correct:
                logging.info(f"   Confidence: {scores.get(predicted_bucket, 0.0):.3f}")
        
        results["accuracy"] = (results["passed"] / results["total_tests"]) * 100
        
        logging.info(f"📊 Validation Results: {results['passed']}/{results['total_tests']} tests passed")
        logging.info(f"🎯 Accuracy: {results['accuracy']:.1f}%")
        
        return results
    
    def analyze_classification_quality(self, chunks: List) -> Dict:
        """
        Analyzes the overall quality of chunk classification
        """
        analysis = {
            "total_chunks": len(chunks),
            "confidence_distribution": {
                "high_confidence": 0,  # > 0.5
                "medium_confidence": 0,  # 0.2 - 0.5
                "low_confidence": 0     # < 0.2
            },
            "bucket_quality_scores": {},
            "problematic_chunks": [],
            "recommendations": []
        }
        
        confidence_scores = []
        bucket_confidences = {}
        
        for chunk in chunks:
            confidence = chunk.metadata.get("confidence", 0.0)
            bucket = chunk.metadata.get("bucket", "unknown")
            
            confidence_scores.append(confidence)
            
            if bucket not in bucket_confidences:
                bucket_confidences[bucket] = []
            bucket_confidences[bucket].append(confidence)
            
            # Categorize by confidence
            if confidence > 0.5:
                analysis["confidence_distribution"]["high_confidence"] += 1
            elif confidence > 0.2:
                analysis["confidence_distribution"]["medium_confidence"] += 1
            else:
                analysis["confidence_distribution"]["low_confidence"] += 1
                
                # Identify problematic chunks
                analysis["problematic_chunks"].append({
                    "content_preview": chunk.page_content[:150],
                    "bucket": bucket,
                    "confidence": confidence,
                    "source": chunk.metadata.get("source_pdf", "unknown")
                })
        
        # Calculate quality scores per bucket
        for bucket, confidences in bucket_confidences.items():
            avg_confidence = sum(confidences) / len(confidences)
            analysis["bucket_quality_scores"][bucket] = {
                "average_confidence": avg_confidence,
                "chunk_count": len(confidences),
                "min_confidence": min(confidences),
                "max_confidence": max(confidences)
            }
        
        # Generate recommendations
        low_conf_percentage = (analysis["confidence_distribution"]["low_confidence"] / len(chunks)) * 100
        
        if low_conf_percentage > 20:
            analysis["recommendations"].append(
                f"⚠️ {low_conf_percentage:.1f}% of chunks have low confidence. Consider refining bucket keywords or patterns."
            )
        
        if "misc" in bucket_confidences and len(bucket_confidences["misc"]) > len(chunks) * 0.3:
            analysis["recommendations"].append(
                "⚠️ Too many chunks classified as 'misc'. Consider adding more specific buckets."
            )
        
        return analysis
    
    def suggest_bucket_improvements(self, chunks: List, min_frequency: int = 5) -> Dict:
        """
        Suggests bucket improvements based on chunk analysis
        """
        suggestions = {
            "new_bucket_candidates": [],
            "keyword_suggestions": {},
            "pattern_suggestions": {}
        }
        
        # Analyze low-confidence chunks to identify patterns
        low_confidence_chunks = [
            chunk for chunk in chunks 
            if chunk.metadata.get("confidence", 0.0) < 0.2
        ]
        
        # Identify frequent keywords in poorly classified chunks
        word_frequency = {}
        for chunk in low_confidence_chunks:
            words = chunk.page_content.lower().split()
            for word in words:
                if len(word) > 3 and word.isalpha():  # Filter significant words
                    word_frequency[word] = word_frequency.get(word, 0) + 1
        
        # Suggest new keywords
        frequent_words = {word: freq for word, freq in word_frequency.items() if freq >= min_frequency}
        
        if frequent_words:
            suggestions["keyword_suggestions"] = {
                "frequent_unclassified_terms": frequent_words,
                "suggestion": "Consider adding these terms to existing buckets or creating new ones"
            }
        
        return suggestions

def main():
    """
    Main function to run validation and analysis
    """
    # Import the classifier from the main file
    from preprocess import ZOHOBucketClassifier
    
    # Initialize validator and classifier
    validator = BucketValidator()
    classifier = ZOHOBucketClassifier()
    
    # Run validation tests
    validation_results = validator.run_validation_tests(classifier)
    
    # Save validation results
    with open("validation_results.json", "w") as f:
        json.dump(validation_results, f, indent=2, default=str)
    
    # If you have processed chunks, analyze quality
    chunks_file = "processed_chunks.json"  # Assuming you save processed chunks
    
    if Path(chunks_file).exists():
        with open(chunks_file, "r") as f:
            chunks_data = json.load(f)
        
        # Simulate chunk objects for analysis
        # (In production, you would load real Document objects)
        mock_chunks = []
        for chunk_data in chunks_data:
            class MockChunk:
                def __init__(self, content, metadata):
                    self.page_content = content
                    self.metadata = metadata
            
            mock_chunks.append(MockChunk(
                chunk_data.get("content", ""),
                chunk_data.get("metadata", {})
            ))
        
        # Analyze quality
        quality_analysis = validator.analyze_classification_quality(mock_chunks)
        
        # Suggest improvements
        improvements = validator.suggest_bucket_improvements(mock_chunks)
        
        # Save analyses
        with open("quality_analysis.json", "w") as f:
            json.dump(quality_analysis, f, indent=2, default=str)
        
        with open("improvement_suggestions.json", "w") as f:
            json.dump(improvements, f, indent=2, default=str)
        
        logging.info("📊 Quality analysis complete!")
        logging.info(f"💡 {len(quality_analysis['recommendations'])} recommendations generated")
    
    logging.info("✅ Validation and analysis complete!")
    logging.info("📁 Check the generated JSON files for detailed results")

if __name__ == "__main__":
    main()