import unittest
from unittest.mock import MagicMock
from transfer_service import TransferEngine

class TestTransferEngineInit(unittest.TestCase):
    def test_init(self):
        """Test that TransferEngine initializes correctly with two clients."""
        mock_bot = MagicMock()
        mock_userbot = MagicMock()

        # This should succeed without TypeError
        engine = TransferEngine(mock_bot, mock_userbot)

        self.assertEqual(engine.bot, mock_bot)
        self.assertEqual(engine.userbot, mock_userbot)
        self.assertEqual(engine.active_tasks, {})
        print("TransferEngine initialized successfully.")

if __name__ == '__main__':
    unittest.main()
