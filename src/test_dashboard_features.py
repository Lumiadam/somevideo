import unittest
import sqlite3
import os
import sys

# Ensure workspace path is correct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_manager import get_all_movies, get_movie
from src.recommender import get_recommendations

class TestDashboardFeatures(unittest.TestCase):
    def setUp(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "recommender.db")
        self.assertTrue(os.path.exists(self.db_path), "Database file does not exist!")

    def test_database_schema(self):
        """Test if the Movie table has cover_url and video_preview_url, and Group_Movies table exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check Movie columns
        cursor.execute("PRAGMA table_info(Movie)")
        columns = [row[1] for row in cursor.fetchall()]
        self.assertIn("cover_url", columns)
        self.assertIn("video_preview_url", columns)
        
        # Check Group_Movies existence
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Group_Movies'")
        self.assertEqual(cursor.fetchone()[0], "Group_Movies")
        
        conn.close()

    def test_group_isolation_in_queries(self):
        """Test if query results for a group only show movies associated with that group."""
        # Group 2 (搞笑短影音同好會): Movie 4, 10, 14
        movies_g2 = get_all_movies(username="user1", group_id=2)
        for m in movies_g2:
            self.assertIn(m["id"], [4, 10, 14])
            
        # Group 3 (驚悚懸疑同好會): Movie 5, 9, 15
        movies_g3 = get_all_movies(username="user1", group_id=3)
        for m in movies_g3:
            self.assertIn(m["id"], [5, 9, 15])

    def test_group_isolation_in_recommendations(self):
        """Test if recommendations generated for a user in a specific group only belong to that group."""
        # Get recommendations for user3 (a member of Group 2 & 3) inside Group 2
        recs_g2 = get_recommendations(username="user3", group_id=2, limit=5)
        for r in recs_g2:
            self.assertIn(r["id"], [4, 10, 14])
            
        # Inside Group 3
        recs_g3 = get_recommendations(username="user3", group_id=3, limit=5)
        for r in recs_g3:
            self.assertIn(r["id"], [5, 9, 15])

    def test_group_movie_sharing_and_approval(self):
        """Test sharing a movie to a group, auditing it, and validating isolation behavior."""
        from src.data_manager import add_movie_to_group, approve_group_movie, reject_group_movie, get_group_pending_movies
        
        # Clean up first to ensure clean state
        reject_group_movie(group_id=2, movie_id=1)
        
        # 1. Share movie 1 to Group 2 as Pending
        add_movie_to_group(group_id=2, movie_id=1, shared_by="user1", status="Pending")
        
        # 2. Verify it is pending
        pending = get_group_pending_movies(group_id=2)
        pending_ids = [m["id"] for m in pending]
        self.assertIn(1, pending_ids)
        
        # 3. Verify it does NOT show up in Group 2's active movie list yet
        movies_g2 = get_all_movies(username="user1", group_id=2)
        movies_g2_ids = [m["id"] for m in movies_g2]
        self.assertNotIn(1, movies_g2_ids)
        
        # 4. Approve the movie
        approve_group_movie(group_id=2, movie_id=1)
        
        # 5. Verify it is no longer pending
        pending_after = get_group_pending_movies(group_id=2)
        pending_ids_after = [m["id"] for m in pending_after]
        self.assertNotIn(1, pending_ids_after)
        
        # 6. Verify it shows up in Group 2's active list now
        movies_g2_after = get_all_movies(username="user1", group_id=2)
        movies_g2_ids_after = [m["id"] for m in movies_g2_after]
        self.assertIn(1, movies_g2_ids_after)
        
        # Clean up
        reject_group_movie(group_id=2, movie_id=1)

if __name__ == "__main__":
    unittest.main()
