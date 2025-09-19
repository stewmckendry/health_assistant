'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Star,
  Send,
  Check,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface FeedbackButtonsProps {
  traceId: string;
  sessionId: string;
  onFeedback: (feedback: any) => void;
  context?: 'chat' | 'triage';
}

export function FeedbackButtons({
  traceId,
  sessionId,
  onFeedback,
  context = 'chat',
}: FeedbackButtonsProps) {
  const [rating, setRating] = useState<number | null>(null);
  const [hoveredRating, setHoveredRating] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const [showCommentDialog, setShowCommentDialog] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [tempRating, setTempRating] = useState<number | null>(null);

  const handleRating = (value: number) => {
    setTempRating(value);
    setShowCommentDialog(true);
  };

  const handleCommentSubmit = () => {
    if (tempRating !== null) {
      setRating(tempRating);
      onFeedback({
        traceId,
        sessionId,
        rating: tempRating,
        comment: comment.trim() || null,
      });
      setComment('');
      setShowCommentDialog(false);
      setSubmitted(true);
      
      // Show confirmation for 3 seconds
      setTimeout(() => {
        setSubmitted(false);
      }, 3000);
    }
  };

  const handleSkip = () => {
    if (tempRating !== null) {
      setRating(tempRating);
      onFeedback({
        traceId,
        sessionId,
        rating: tempRating,
        comment: null,
      });
      setShowCommentDialog(false);
      setSubmitted(true);
      
      // Show confirmation for 3 seconds
      setTimeout(() => {
        setSubmitted(false);
      }, 3000);
    }
  };

  // If feedback has been submitted, show confirmation
  if (submitted) {
    return (
      <div className="flex items-center gap-2 mt-2 text-sm text-green-600">
        <Check className="h-4 w-4" />
        <span>Thank you for your feedback!</span>
      </div>
    );
  }

  // If rating has been given, show the selected rating (read-only)
  if (rating !== null && !submitted) {
    return (
      <div className="flex items-center gap-2 mt-2">
        <span className="text-xs text-muted-foreground">Your rating:</span>
        <div className="flex gap-0.5">
          {[1, 2, 3, 4, 5].map((value) => (
            <Star
              key={value}
              className={cn(
                'h-4 w-4',
                value <= rating
                  ? 'fill-yellow-500 text-yellow-500'
                  : 'text-muted-foreground/30'
              )}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center gap-2 mt-2">
        <span className="text-xs text-muted-foreground">
          Rate this {context === 'triage' ? 'assessment' : 'response'}:
        </span>
        <div className="flex gap-0.5">
          {[1, 2, 3, 4, 5].map((value) => (
            <Button
              key={value}
              variant="ghost"
              size="sm"
              onClick={() => handleRating(value)}
              onMouseEnter={() => setHoveredRating(value)}
              onMouseLeave={() => setHoveredRating(null)}
              className="h-7 w-7 p-0 hover:bg-transparent"
            >
              <Star
                className={cn(
                  'h-4 w-4 transition-colors',
                  (hoveredRating !== null && value <= hoveredRating) ||
                  (rating !== null && value <= rating)
                    ? 'fill-yellow-500 text-yellow-500'
                    : 'text-muted-foreground hover:text-yellow-500'
                )}
              />
            </Button>
          ))}
        </div>
      </div>

      <Dialog open={showCommentDialog} onOpenChange={setShowCommentDialog}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Thank you for your feedback!</DialogTitle>
            <DialogDescription>
              You rated this {context === 'triage' ? 'assessment' : 'response'} {tempRating} out of 5 stars. 
              Would you like to add any additional comments{context === 'triage' ? ' about the triage assessment' : ''}?
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <Textarea
              placeholder={
                context === 'triage' 
                  ? "Share feedback about the accuracy, usefulness, or any concerns... (optional)"
                  : "Share any specific feedback about this response... (optional)"
              }
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="min-h-[100px]"
            />
          </div>
          <DialogFooter className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleSkip}
            >
              Skip
            </Button>
            <Button
              onClick={handleCommentSubmit}
            >
              <Send className="h-4 w-4 mr-1" />
              Submit Feedback
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}