import os
import resend
from typing import Optional
from app.config import settings

resend.api_key = settings.RESEND_API_KEY

# Common sender — user must verify a domain with Resend to change this
FROM_ADDR = "onboarding@resend.dev"


def _send(to_email: str, subject: str, html: str) -> bool:
    """Send an email via Resend. Falls back to print if no API key configured."""
    if not settings.RESEND_API_KEY:
        print(f"[EMAIL STUB] To: {to_email} | Subject: {subject}")
        print(f"[EMAIL STUB] Body: {html[:200]}...")
        return True

    try:
        r = resend.Emails.send({
            "from": FROM_ADDR,
            "to": to_email,
            "subject": subject,
            "html": html,
        })
        print(f"Email sent to {to_email}: {r}")
        return True
    except Exception as e:
        print(f"Error sending email to {to_email}: {e}")
        return False


def send_password_reset(to_email: str, token: str) -> bool:
    return _send(
        to_email=to_email,
        subject="CubeRail — Password Reset",
        html=f"""
        <h2>Password Reset</h2>
        <p>Your password reset token is: <strong>{token}</strong></p>
        <p>If you did not request this, you can safely ignore this email.</p>
        """,
    )


def send_game_invite(to_email: str, inviter_name: str, game_id: str) -> bool:
    return _send(
        to_email=to_email,
        subject="CubeRail — You've been invited to a game!",
        html=f"""
        <h2>Game Invitation</h2>
        <p><strong>{inviter_name}</strong> has invited you to play CubeRail!</p>
        <p><a href="http://localhost:5173/game/{game_id}">Join the game</a></p>
        """,
    )


def send_game_started(to_email: str, game_id: str) -> bool:
    return _send(
        to_email=to_email,
        subject="CubeRail — Game has started!",
        html=f"""
        <h2>Game Started</h2>
        <p>The game has started!</p>
        <p><a href="http://localhost:5173/game/{game_id}">Go to the game</a></p>
        """,
    )


def send_your_turn(to_email: str, game_id: str, opponent_name: Optional[str] = None) -> bool:
    opponent_part = f" {opponent_name} has moved and" if opponent_name else ""
    return _send(
        to_email=to_email,
        subject="CubeRail — Your turn!",
        html=f"""
        <h2>Your Turn</h2>
        <p>{opponent_part} it's your turn!</p>
        <p><a href="http://localhost:5173/game/{game_id}">Make your move</a></p>
        """,
    )


def send_game_over(to_email: str, game_id: str, winner_name: Optional[str] = None) -> bool:
    winner_part = f" Winner: {winner_name}." if winner_name else ""
    return _send(
        to_email=to_email,
        subject="CubeRail — Game Over!",
        html=f"""
        <h2>Game Over</h2>
        <p>The game has ended.{winner_part}</p>
        <p><a href="http://localhost:5173/game/{game_id}">View final scores</a></p>
        """,
    )


def send_player_joined(to_email: str, game_id: str, joiner_name: str) -> bool:
    return _send(
        to_email=to_email,
        subject="CubeRail — A player joined your game",
        html=f"""
        <h2>Player Joined</h2>
        <p><strong>{joiner_name}</strong> has joined your game!</p>
        <p><a href="http://localhost:5173/game/{game_id}">See the lobby</a></p>
        """,
    )
