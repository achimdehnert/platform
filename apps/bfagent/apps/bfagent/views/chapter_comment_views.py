"""
Chapter-Level Comment Views
Allows readers to add comments directly on chapters
"""
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Q

from ..models import (
    BookChapters,
    Comment,
    ReviewRound,
    ReviewParticipant,
)


@login_required
def chapter_comment_add(request, chapter_id):
    """Add a comment to a chapter"""
    chapter = get_object_or_404(BookChapters, pk=chapter_id)
    
    # Check if user has access (author or participant in active review round)
    has_access = (
        chapter.project.user == request.user or
        chapter.project.owner == request.user or
        ReviewParticipant.objects.filter(
            review_round__project=chapter.project,
            user=request.user,
            status='active'
        ).exists()
    )
    
    if not has_access:
        messages.error(request, "You don't have permission to comment on this chapter.")
        return redirect('bfagent:chapter-detail', pk=chapter_id)
    
    if request.method == 'POST':
        comment_type = request.POST.get('comment_type', 'general')
        text = request.POST.get('text', '').strip()
        review_round_id = request.POST.get('review_round_id')
        
        if not text:
            messages.error(request, "Comment text is required.")
            return redirect('bfagent:chapter-detail', pk=chapter_id)
        
        # Get review round if specified, or create/get default one
        review_round = None
        if review_round_id:
            try:
                review_round = ReviewRound.objects.get(pk=review_round_id)
            except ReviewRound.DoesNotExist:
                pass
        
        # If no review round specified, create/get a default one for general comments
        if not review_round:
            review_round, created = ReviewRound.objects.get_or_create(
                project=chapter.project,
                title='General Comments',
                defaults={
                    'description': 'Default review round for general chapter comments',
                    'status': 'active',
                    'created_by': request.user,
                    'allow_comments': True,
                    'allow_ratings': False,
                    'comments_visible_to_others': True,
                }
            )
        
        # Create comment
        comment = Comment.objects.create(
            review_round=review_round,
            chapter=chapter,
            author=request.user,
            text=text,
            comment_type=comment_type,
            status='open'
        )
        
        # Update stats if in review round
        if review_round:
            review_round.update_stats()
            
            # Update participant stats
            try:
                participant = ReviewParticipant.objects.get(
                    review_round=review_round,
                    user=request.user
                )
                participant.update_stats()
            except ReviewParticipant.DoesNotExist:
                pass
        
        messages.success(request, f'{comment.get_comment_type_display()} comment added successfully!')
        
        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'comment_id': comment.id,
                'message': 'Comment added successfully!'
            })
        
        return redirect('bfagent:chapter-detail', pk=chapter_id)
    
    # GET request - show form
    # Get active review rounds for this chapter's project
    active_rounds = ReviewRound.objects.filter(
        project=chapter.project,
        status='active'
    ).filter(
        Q(created_by=request.user) |
        Q(participants__user=request.user)
    ).distinct()
    
    context = {
        'chapter': chapter,
        'active_rounds': active_rounds,
    }
    
    return render(request, 'bfagent/chapter/comment_form.html', context)


@login_required
def chapter_comments_list(request, chapter_id):
    """List all comments for a chapter"""
    chapter = get_object_or_404(BookChapters, pk=chapter_id)
    
    # Get comments
    comments = Comment.objects.filter(
        chapter=chapter
    ).select_related('author', 'review_round').order_by('-created_at')
    
    # Filter by status if specified
    status = request.GET.get('status')
    if status:
        comments = comments.filter(status=status)
    
    # Filter by type if specified
    comment_type = request.GET.get('type')
    if comment_type:
        comments = comments.filter(comment_type=comment_type)
    
    # Stats
    stats = {
        'total': comments.count(),
        'open': comments.filter(status='open').count(),
        'resolved': comments.filter(status='resolved').count(),
        'by_type': comments.values('comment_type').annotate(count=Count('id')),
    }
    
    context = {
        'chapter': chapter,
        'comments': comments,
        'stats': stats,
    }
    
    return render(request, 'bfagent/chapter/comments_list.html', context)


@login_required
@require_POST
def chapter_comment_toggle_status(request, comment_id):
    """Toggle comment status (open <-> resolved)"""
    comment = get_object_or_404(Comment, pk=comment_id)
    
    # Only author or chapter owner can toggle status
    if request.user != comment.author and request.user != comment.chapter.project.user:
        messages.error(request, "You don't have permission to change comment status.")
        return redirect('bfagent:chapter-detail', pk=comment.chapter.pk)
    
    # Toggle status
    if comment.status == 'open':
        comment.status = 'resolved'
        messages.success(request, 'Comment marked as resolved.')
    else:
        comment.status = 'open'
        messages.success(request, 'Comment reopened.')
    
    comment.save()
    
    # Return JSON for AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'status': comment.status,
            'status_display': comment.get_status_display()
        })
    
    return redirect('bfagent:chapter-detail', pk=comment.chapter.pk)


@login_required
@require_POST
def chapter_comment_delete(request, comment_id):
    """Delete a comment"""
    comment = get_object_or_404(Comment, pk=comment_id)
    chapter_id = comment.chapter.pk
    
    # Only author can delete their own comment
    if request.user != comment.author:
        messages.error(request, "You can only delete your own comments.")
        return redirect('bfagent:chapter-detail', pk=chapter_id)
    
    comment.delete()
    messages.success(request, 'Comment deleted.')
    
    # Return JSON for AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('bfagent:chapter-detail', pk=chapter_id)
