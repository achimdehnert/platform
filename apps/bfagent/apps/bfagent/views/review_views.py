"""
Views for Review System
"""
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.utils import timezone
from django.db.models import Q, Count, Avg

from ..models import (
    ReviewRound,
    ReviewParticipant,
    Comment,
    ChapterRating,
    BookProjects,
)


class ReviewRoundListView(LoginRequiredMixin, ListView):
    """List all review rounds for current user"""
    model = ReviewRound
    template_name = 'bfagent/review/round_list.html'
    context_object_name = 'review_rounds'
    paginate_by = 20

    def get_queryset(self):
        """Get rounds created by current user"""
        return ReviewRound.objects.filter(
            created_by=self.request.user
        ).select_related('project').prefetch_related('participants')


class ReviewRoundDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a review round"""
    model = ReviewRound
    template_name = 'bfagent/review/round_detail.html'
    context_object_name = 'review_round'

    def get_queryset(self):
        """Ensure user can only see own rounds"""
        return ReviewRound.objects.filter(
            created_by=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        review_round = self.object

        # Get participants
        context['participants'] = review_round.participants.select_related('user').all()

        # Get recent comments
        context['recent_comments'] = review_round.comments.select_related(
            'author', 'chapter'
        ).order_by('-created_at')[:10]

        # Get statistics
        context['stats'] = {
            'total_comments': review_round.total_comments,
            'unread_comments': review_round.unread_comments,
            'total_participants': review_round.total_participants,
            'total_ratings': review_round.total_ratings,
            'average_rating': review_round.average_rating,
            'progress': review_round.get_progress(),
        }

        # Comments by chapter
        context['comments_by_chapter'] = Comment.objects.filter(
            review_round=review_round
        ).values('chapter__title').annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        return context


class ReviewRoundCreateView(LoginRequiredMixin, CreateView):
    """Create a new review round"""
    model = ReviewRound
    template_name = 'bfagent/review/round_form.html'
    fields = [
        'project',
        'title',
        'description',
        'start_date',
        'end_date',
        'allow_comments',
        'allow_ratings',
        'comments_visible_to_others',
    ]

    def get_form(self, form_class=None):
        """Customize form"""
        form = super().get_form(form_class)

        # Filter projects to user's own
        form.fields['project'].queryset = BookProjects.objects.filter(
            Q(user=self.request.user) | Q(owner=self.request.user)
        )

        # Pre-select project from URL parameter
        project_id = self.request.GET.get('project')
        if project_id and not form.instance.pk:
            try:
                project = BookProjects.objects.get(pk=project_id)
                form.fields['project'].initial = project
            except BookProjects.DoesNotExist:
                pass

        # Set default start date to now
        if not form.instance.pk:
            form.fields['start_date'].initial = timezone.now()

        # Add CSS classes
        for field_name, field in form.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name == 'description':
                field.widget.attrs['rows'] = 4

        return form

    def form_valid(self, form):
        """Set created_by to current user"""
        form.instance.created_by = self.request.user
        form.instance.status = 'draft'
        messages.success(
            self.request,
            f'Review Round "{form.instance.title}" created successfully!'
        )
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to detail view"""
        return reverse('bfagent:review-round-detail', kwargs={'pk': self.object.pk})


class ReviewRoundUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing review round"""
    model = ReviewRound
    template_name = 'bfagent/review/round_form.html'
    fields = [
        'title',
        'description',
        'status',
        'start_date',
        'end_date',
        'allow_comments',
        'allow_ratings',
        'comments_visible_to_others',
    ]

    def get_queryset(self):
        """Ensure user can only edit own rounds"""
        return ReviewRound.objects.filter(created_by=self.request.user)

    def get_form(self, form_class=None):
        """Customize form"""
        form = super().get_form(form_class)

        # Add CSS classes
        for field_name, field in form.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name == 'description':
                field.widget.attrs['rows'] = 4

        return form

    def form_valid(self, form):
        """Add success message"""
        messages.success(
            self.request,
            f'Review Round "{form.instance.title}" updated successfully!'
        )
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect to detail view"""
        return reverse('bfagent:review-round-detail', kwargs={'pk': self.object.pk})


class ReviewRoundDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a review round"""
    model = ReviewRound
    template_name = 'bfagent/review/round_confirm_delete.html'
    success_url = reverse_lazy('bfagent:review-round-list')

    def get_queryset(self):
        """Ensure user can only delete own rounds"""
        return ReviewRound.objects.filter(created_by=self.request.user)

    def delete(self, request, *args, **kwargs):
        """Add success message"""
        messages.success(request, 'Review Round deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
def review_round_start(request, pk):
    """Start a review round (change status to active)"""
    review_round = get_object_or_404(
        ReviewRound,
        pk=pk,
        created_by=request.user
    )

    if review_round.status == 'draft':
        review_round.status = 'active'
        review_round.start_date = timezone.now()
        review_round.save()
        messages.success(request, f'Review Round "{review_round.title}" started!')
    else:
        messages.warning(request, 'Review Round is already active.')

    return redirect('bfagent:review-round-detail', pk=pk)


@login_required
def review_round_complete(request, pk):
    """Complete a review round (change status to completed)"""
    review_round = get_object_or_404(
        ReviewRound,
        pk=pk,
        created_by=request.user
    )

    if review_round.status == 'active':
        review_round.status = 'completed'
        review_round.completed_at = timezone.now()
        review_round.save()
        messages.success(request, f'Review Round "{review_round.title}" completed!')
    else:
        messages.warning(request, 'Review Round must be active to complete.')

    return redirect('bfagent:review-round-detail', pk=pk)


@login_required
def review_round_stats(request, pk):
    """Statistics view for review round"""
    review_round = get_object_or_404(
        ReviewRound,
        pk=pk,
        created_by=request.user
    )

    # Update stats first
    review_round.update_stats()

    # Gather detailed statistics
    stats = {
        'review_round': review_round,
        'participants': review_round.participants.all(),
        'comments_by_type': Comment.objects.filter(
            review_round=review_round
        ).values('comment_type').annotate(count=Count('id')),
        'comments_by_status': Comment.objects.filter(
            review_round=review_round
        ).values('status').annotate(count=Count('id')),
        'ratings_by_chapter': ChapterRating.objects.filter(
            review_round=review_round
        ).values(
            'chapter__title', 'chapter__chapter_number'
        ).annotate(
            avg_rating=Avg('overall_rating'),
            count=Count('id')
        ).order_by('chapter__chapter_number'),
        'top_commenters': ReviewParticipant.objects.filter(
            review_round=review_round
        ).order_by('-comments_count')[:5],
    }

    return render(request, 'bfagent/review/round_stats.html', stats)


# Participant Management Views

@login_required
def participant_add(request, pk):
    """Add participant to review round"""
    review_round = get_object_or_404(
        ReviewRound,
        pk=pk,
        created_by=request.user
    )

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role = request.POST.get('role', 'reader')

        from django.contrib.auth.models import User
        user = get_object_or_404(User, pk=user_id)

        # Create participant
        participant, created = ReviewParticipant.objects.get_or_create(
            review_round=review_round,
            user=user,
            defaults={
                'role': role,
                'can_comment': True,
                'can_rate': True,
                'status': 'active',
            }
        )

        if created:
            # Update round stats
            review_round.update_stats()
            messages.success(
                request,
                f'User {user.username} added as {role} to review round.'
            )
        else:
            messages.warning(
                request,
                f'User {user.username} is already a participant.'
            )

    return redirect('bfagent:review-round-detail', pk=pk)


@login_required
def participant_remove(request, pk, participant_id):
    """Remove participant from review round"""
    review_round = get_object_or_404(
        ReviewRound,
        pk=pk,
        created_by=request.user
    )

    participant = get_object_or_404(
        ReviewParticipant,
        pk=participant_id,
        review_round=review_round
    )

    username = participant.user.username
    participant.delete()

    # Update round stats
    review_round.update_stats()

    messages.success(
        request,
        f'User {username} removed from review round.'
    )

    return redirect('bfagent:review-round-detail', pk=pk)
