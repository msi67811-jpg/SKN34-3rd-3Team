from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CalendarEvent(BaseModel):
    model_config = ConfigDict(title="캘린더 일정")
    id: int = Field(description="일정 ID")
    eventType: str = Field(description="종류: TAX 또는 POLICY")
    title: str = Field(description="일정 제목")
    dueDate: date = Field(description="마감일")
    description: str = Field(description="설명")
    policyId: int | None = Field(default=None, description="지원정책 ID (지원금 일정일 때)")


class CalendarResponse(BaseModel):
    model_config = ConfigDict(title="캘린더 응답")
    events: list[CalendarEvent] = Field(description="일정 목록")


class ReminderItem(BaseModel):
    model_config = ConfigDict(title="리마인더")
    reminderId: int = Field(description="리마인더 ID")
    eventId: int = Field(description="일정 ID")
    title: str = Field(description="일정 제목")
    dueDate: date = Field(description="마감일")
    notifyAt: datetime = Field(description="알림 시각")


class ReminderListResponse(BaseModel):
    model_config = ConfigDict(title="리마인더 목록")
    reminders: list[ReminderItem] = Field(description="리마인더들")


class ReminderCreateRequest(BaseModel):
    model_config = ConfigDict(title="리마인더 등록")
    eventId: int = Field(description="일정 ID")
    notifyAt: datetime = Field(description="알림 시각")


class ReminderCreateResponse(BaseModel):
    model_config = ConfigDict(title="리마인더 등록 결과")
    reminderId: int = Field(description="생성된 리마인더 ID")
