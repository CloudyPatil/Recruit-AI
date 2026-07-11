from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer('./models/sbert_model')

def match(resume, job):
    r = model.encode([resume])
    j = model.encode([job])
    score = cosine_similarity(r, j)[0][0]
    return round(float(score * 100), 1)

# Test 1 - Should be HIGH (same domain)
print("Test 1 - Python dev vs Python job:")
print(match(
    "Python developer machine learning tensorflow 3 years experience",
    "Looking for Python ML engineer with tensorflow skills"
))

# Test 2 - Should be LOW (different domain)
print("\nTest 2 - Nurse vs Java job:")
print(match(
    "Registered nurse ICU patient care 5 years hospital",
    "Java spring boot microservices backend developer"
))

# Test 3 - Should be MEDIUM
print("\nTest 3 - Frontend vs Fullstack:")
print(match(
    "React developer HTML CSS JavaScript 2 years",
    "Fullstack developer React Node.js MongoDB required"
))

# Test 4 - Finance match
print("\nTest 4 - Accountant vs Finance:")
print(match(
    "Chartered accountant taxation auditing 4 years experience",
    "Finance manager accounting tax compliance needed"
))